# 1-Bit-PDF 📄🚀

Ein schlankes Web-Tool, um große PDF-Scans in extrem kompakte Schwarz-Weiß-PDFs (1-Bit) zu konvertieren.
Ideal, um Speicherplatz zu sparen und die Lesbarkeit von Dokumenten zu erhöhen.

<img src="./assets/1-bit-pdf_dark.png" alt="1-Bit-PDF Preview" width="400"> <img src="./assets/1-bit-pdf_light.png" alt="1-Bit-PDF Preview" width="400">

## ✨ Features
- **Echtes 1-Bit Schwarz-Weiß:** Nutzt TIFF Group-4-Kompression innerhalb des PDFs.
- **Intelligente Binarisierung:** Wahlweise manueller Schwellwert oder automatischer **Otsu-Algorithmus**.
- **Text-Optimierung:** Integrierte *Unsharp Mask*, um dünne Linien beim Binarisieren zu erhalten.
- **Schnell:** Multi-threaded Verarbeitung der PDF-Seiten für maximale Performance.
- **Privatsphäre:** Die Verarbeitung erfolgt temporär; Dateien werden nach dem Download gelöscht.
- **Style:** Unterstützt Hell- und Dunkelmodus des Browsers.

## 🛠 Technologie
1-Bit-PDF nutzt:
- **Python / Flask** (Backend)
- **PyMuPDF (fitz)** (PDF-Verarbeitung)
- **Pillow** (Bildmanipulation)
- **Numpy** (Mathematische Berechnungen für Otsu)

## 🚀 Installation & Setup

### Voraussetzung
* 1-Bit-PDF ist für den Einsatz auf [OpenMediaVault](https://github.com/openmediavault/openmediavault) mit installiertem `openmediavault-compose` Plugin konzipiert.
* Alternativ lässt sich 1-Bit-PDF mit Portainer bzw. einer Standard-Docker-Umgebung nutzen.

### Schritt 1: Docker Compose Datei erstellen
Navigiere in OpenMediaVault zu `Services` > `Compose` > `Files` > `Add` und erstelle einen neuen Stack namens `1-Bit-PDF`.
Füge dem Stack folgenden Inhalt hinzu:

```text
services:
  pdf-1bit:
    build: .
    container_name: 1-bit-pdf
    ports:
      - "4040:4040"
    restart: unless-stopped
```

### Schritt 2: Dateistruktur vorbereiten
Finde den Ordner `1-bit-pdf` in deinem Config-Verzeichnis und füge die folgenden Dateien in dieser Struktur hinzu.
Wichtig: `index.html` **muss** im Unterordner `/templates` liegen.

```text
1-bit-pdf/
├── app.py
├── Dockerfile
├── requirements.txt
├── docker-compose.yml
└── templates/
    └── index.html 
```

### Schritt 3: Container starten

Kehre in OpenMediaVault zurück zu `Services` > `Compose` > `Files`, wähle den Stack `1-Bit-PDF` und klicke auf `Up`, um das Image lokal zu bauen und den Container zu starten. Der erste Start dauert einen Moment, da das Python-Image geladen und die Abhängigkeiten installiert werden.

## 💻 Nutzung
Öffne ```http://<DEINE-OMV-IP>:4040``` und ziehe eine PDF-Datei per Drag & Drop in das Feld oder klicke darauf, um eine sie umzuwandeln.
Stelle einen Schwellwert ein oder nutze Otsu für eine automatische Erkennung. Der Download der 1-Bit-Datei startet automatisch.


## 🤖 Disclaimer
> Dieses Projekt wurde mit Hilfe von KI erstellt.
