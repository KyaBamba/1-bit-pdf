FROM python:3.12-slim

# Pillow braucht libjpeg für TIFF-Unterstützung (Group-4-Kompression)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libjpeg62-turbo && \
    rm -rf /var/lib/apt/lists/*

# Unprivilegierter App-User – falls die App je kompromittiert wird,
# hat der Angreifer keinen root-Zugriff im Container.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Abhängigkeiten mit gepinnten Versionen installieren.
# Gunicorn ersetzt Flasks eingebauten Dev-Server:
# multi-threaded, produktionstauglich, kein debug-Modus.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Dateien kopieren und Besitz an appuser übergeben
COPY --chown=appuser:appuser . /app

# Ab hier als unprivilegierter User laufen
USER appuser

EXPOSE 4040

# 1 Worker + 4 Threads: Threads teilen denselben Prozessspeicher,
# sodass der in-memory Job-Store für alle Requests (Upload, SSE, Download)
# sichtbar ist. Mehrere Worker würden das jobs-Dict aufsplitten und
# den SSE-Fortschritt zuverlässig brechen.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:4040", "app:app"]