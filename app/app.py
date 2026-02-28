from flask import Flask, request, render_template, send_file, jsonify, Response
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz  # PyMuPDF
from PIL import Image, ImageFilter
import numpy as np
import io
import threading
import uuid
import json
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# 300 DPI für scharfen Text (war: 200 DPI)
RENDER_DPI = 300

# Jobs älter als diese Zeit (Sekunden) werden automatisch gelöscht.
JOB_TTL = 600  # 10 Minuten

# In-Memory Job-Store: job_id → dict mit Fortschritt, Ergebnis, Fehler
jobs: dict = {}
jobs_lock = threading.Lock()


# ── Aufräumen abgelaufener Jobs ───────────────────────────────────────────────

def _cleanup_loop() -> None:
    """Läuft als Daemon-Thread und löscht abgelaufene Jobs jede Minute."""
    while True:
        # Alle 60 Sekunden prüfen
        time.sleep(60) 
        cutoff = time.monotonic() - JOB_TTL
        with jobs_lock:
            expired = [jid for jid, j in jobs.items() if j['created_at'] < cutoff]
            for jid in expired:
                del jobs[jid]

threading.Thread(target=_cleanup_loop, daemon=True, name="job-cleanup").start()


# ── Otsu-Schwellenwert ────────────────────────────────────────────────────────

def otsu_threshold(gray_array: np.ndarray) -> int:
    """Berechnet den optimalen Schwellenwert nach Otsu (0–255)."""
    hist, _ = np.histogram(gray_array, bins=256, range=(0, 256))
    hist = hist.astype(float)
    total = gray_array.size
    sum_total = np.dot(np.arange(256), hist)

    sum_bg, w_bg, best_thresh, best_var = 0.0, 0.0, 0, 0.0
    for t in range(256):
        w_bg += hist[t]
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / w_bg
        mean_fg = (sum_total - sum_bg) / w_fg
        var = w_bg * w_fg * (mean_bg - mean_fg) ** 2
        if var > best_var:
            best_var, best_thresh = var, t

    return best_thresh


# ── Seitenverarbeitung ────────────────────────────────────────────────────────

def process_page(args: tuple) -> bytes:
    """
    Verarbeitet eine einzelne Seite (thread-safe):
    Unsharp Mask → Threshold (manuell oder Otsu) → 1-Bit ohne Dithering → TIFF Group-4.
    Wirft bei Fehler eine Exception – wird im Aufrufer behandelt.
    """
    samples, width, height, threshold_pixel = args

    img = Image.frombytes("L", (width, height), samples)

    # Kanten schärfen vor der Binarisierung – verhindert, dass dünne
    # Buchstabenstriche beim Threshold verschwinden.
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=150, threshold=2))

    # threshold_pixel == 0 → Otsu pro Seite berechnen
    if threshold_pixel == 0:
        t = otsu_threshold(np.array(img))
    else:
        t = threshold_pixel

    # dither=NONE: kein Floyd-Steinberg – verhindert fuzzy Text-Ränder
    img = img.point(lambda p: 255 if p > t else 0).convert(
        "1", dither=Image.Dither.NONE
    )

    buf = io.BytesIO()
    img.save(buf, format="TIFF", compression="group4")
    return buf.getvalue()


def run_conversion(job_id: str, pdf_bytes: bytes, threshold_pixel: int) -> None:
    """Läuft im Hintergrund-Thread. Schreibt Fortschritt in den Job-Store."""
    try:
        src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total = len(src_doc)

        with jobs_lock:
            jobs[job_id]['total'] = total

        # Seiten rendern – single-threaded, da fitz nicht thread-safe ist
        mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
        page_args = []
        for page in src_doc:
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            page_args.append((pix.samples, pix.width, pix.height, threshold_pixel))

        # Threshold + Kompression parallel; Fehler pro Future explizit abfangen
        tiff_pages = [None] * total
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_page, args): i
                       for i, args in enumerate(page_args)}
            for future in as_completed(futures):
                i = futures[future]
                exc = future.exception()
                if exc:
                    raise RuntimeError(f"Fehler auf Seite {i + 1}: {exc}") from exc
                tiff_pages[i] = future.result()
                with jobs_lock:
                    jobs[job_id]['progress'] += 1

        # Seiten zu einem PDF zusammensetzen
        out_doc = fitz.open()
        for tiff_bytes, (_, w, h, _) in zip(tiff_pages, page_args):
            width_pt  = w * 72 / RENDER_DPI
            height_pt = h * 72 / RENDER_DPI
            new_page  = out_doc.new_page(width=width_pt, height=height_pt)
            new_page.insert_image(new_page.rect, stream=tiff_bytes)

        with jobs_lock:
            jobs[job_id]['result'] = out_doc.tobytes(deflate=True)
            jobs[job_id]['done']   = True

    except Exception as e:
        with jobs_lock:
            jobs[job_id]['error'] = str(e)
            jobs[job_id]['done']  = True


# ── Routen ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'Keine Datei hochgeladen'}), 400

        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400

        safe_name = secure_filename(file.filename)
        if not safe_name.lower().endswith('.pdf'):
            return jsonify({'error': 'Nur PDF-Dateien erlaubt'}), 400

        # Otsu-Modus wenn Checkbox gesetzt, sonst manueller Slider-Wert
        if request.form.get('auto_threshold'):
            threshold_pixel = 0  # → Otsu pro Seite
        else:
            threshold_val = request.form.get('threshold', '50')
            try:
                threshold_int = int(threshold_val)
                if not (1 <= threshold_int <= 99):
                    threshold_int = 50
            except ValueError:
                threshold_int = 50
            threshold_pixel = int(threshold_int / 100 * 255)

        pdf_bytes = file.read()

        job_id = str(uuid.uuid4())
        with jobs_lock:
            jobs[job_id] = {
                'progress':   0,
                'total':      0,
                'done':       False,
                'result':     None,
                'error':      None,
                'filename':   safe_name,
                'created_at': time.monotonic(),
            }

        threading.Thread(
            target=run_conversion,
            args=(job_id, pdf_bytes, threshold_pixel),
            daemon=True,
        ).start()

        return jsonify({'job_id': job_id})

    return render_template('index.html')


@app.route('/progress/<job_id>')
def progress(job_id: str):
    """Server-Sent Events: schickt nach jeder fertigen Seite ein Update."""
    def stream():
        while True:
            with jobs_lock:
                job = jobs.get(job_id)

            if not job:
                yield f"data: {json.dumps({'error': 'Job nicht gefunden'})}\n\n"
                break

            if job.get('error'):
                yield f"data: {json.dumps({'error': job['error']})}\n\n"
                break

            payload = {
                'progress': job['progress'],
                'total':    job['total'],
                'done':     job['done'],
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if job['done']:
                break

            time.sleep(0.1)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/download/<job_id>')
def download(job_id: str):
    """Liefert das fertige PDF aus und räumt den Job danach auf."""
    with jobs_lock:
        job = jobs.get(job_id)

    if not job or not job['done'] or not job['result']:
        return "Job nicht gefunden oder noch nicht fertig", 404

    result    = job['result']
    safe_name = job['filename']
    name_without_ext, ext = safe_name.rsplit('.', 1)
    new_filename = f"{name_without_ext}_1bit.{ext}"

    with jobs_lock:
        del jobs[job_id]

    return send_file(
        io.BytesIO(result),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=new_filename,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4040, debug=False)