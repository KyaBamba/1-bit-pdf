# 1-Bit-PDF 📄🚀

Ein schlankes Web-Tool, um große PDF-Scans in extrem kompakte Schwarz-Weiß-PDFs (1-Bit) zu konvertieren. Ideal, um Speicherplatz zu sparen und die Lesbarkeit von Dokumenten zu erhöhen.

## ✨ Features
- **Echtes 1-Bit Schwarz-Weiß:** Nutzt TIFF Group-4-Kompression innerhalb des PDFs.
- **Intelligente Binarisierung:** Wahlweise manueller Schwellwert oder automatischer **Otsu-Algorithmus**.
- **Text-Optimierung:** Integrierte *Unsharp Mask*, um dünne Linien beim Binarisieren zu erhalten.
- **Schnell:** Multi-threaded Verarbeitung der PDF-Seiten für maximale Performance.
- **Privatsphäre:** Die Verarbeitung erfolgt temporär; Dateien werden nach dem Download gelöscht.

## 🛠 Technik
Das Tool basiert auf:
- **Python / Flask** (Backend)
- **PyMuPDF (fitz)** (PDF-Verarbeitung)
- **Pillow** (Bildmanipulation)
- **Numpy** (Mathematische Berechnungen für Otsu)

## 🚀 Installation & Start

1. Repository klonen:
   ```bash
   git clone [https://github.com/DEIN_USERNAME/1-bit-pdf.git](https://github.com/DEIN_USERNAME/1-bit-pdf.git)