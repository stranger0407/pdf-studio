<div align="center">

# PDF Studio

**Your local PDF toolkit — OCR, Compress, and Restyle. Fast, private, 100% local.**

A modular PDF processing app with three powerful tools. All processing runs on your machine. Your files never leave your computer.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Electron](https://img.shields.io/badge/Electron-29-47848F?style=flat-square&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## ✨ Tools

| Tool | Description |
|------|-------------|
| **🔍 OCR** | Convert scanned PDFs into searchable documents (3 quality presets, parallel processing) |
| **📦 Compress** | Reduce PDF file size with 4 presets including Custom mode (JPEG quality, DPI, grayscale, metadata) |
| **🎨 Restyle** | Change text and background colors of any PDF — no OCR required |

---

## 🖥️ Desktop App

PDF Studio is available as a **standalone Windows installer** — no Python, Node.js, or Tesseract installation needed.

### Download & Install

1. Download `PDF-Studio-1.0.0-setup.exe` from the [Releases](https://github.com/stranger0407/pdf-studio/releases) page
2. Run the installer
3. Launch **PDF Studio** from your Start Menu

The desktop app bundles the full backend (FastAPI + PyMuPDF + pikepdf + Tesseract) and frontend into a single Electron window.

### Build from Source

```bash
# 1. Build the frontend
cd frontend && npm install && npm run build && cd ..

# 2. Build the backend (requires Python + PyInstaller)
cd backend && pip install -r requirements.txt && pip install pyinstaller
python -m PyInstaller pdf_studio_backend.spec --distpath dist --noconfirm && cd ..

# 3. Copy Tesseract to vendor (Windows)
# Place tesseract/ folder into desktop/vendor/

# 4. Build the installer
cd desktop && npm install && npx electron-builder --win --config
```

The installer will be generated at `dist-desktop/PDF-Studio-1.0.0-setup.exe`.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        PDF Studio                                │
│  ┌──────────────┐      HTTP API      ┌────────────────────────┐  │
│  │   React UI   │  ◄───────────────► │   FastAPI Backend      │  │
│  │  (Vite:5173) │                    │   (Uvicorn:8000)       │  │
│  │              │                    │                        │  │
│  │  ┌────────┐  │                    │  ┌──────────────────┐  │  │
│  │  │ OCR    │  │                    │  │ OCR Pipeline     │  │  │
│  │  │ Tool   │  │                    │  │ (Tesseract+fitz) │  │  │
│  │  ├────────┤  │                    │  ├──────────────────┤  │  │
│  │  │Compress│  │                    │  │ Compress Pipeline│  │  │
│  │  │ Tool   │  │                    │  │ (pikepdf+Pillow) │  │  │
│  │  ├────────┤  │                    │  ├──────────────────┤  │  │
│  │  │Restyle │  │                    │  │ Restyle Pipeline │  │  │
│  │  │ Tool   │  │                    │  │ (PyMuPDF/fitz)   │  │  │
│  │  └────────┘  │                    │  └──────────────────┘  │  │
│  └──────────────┘                    └────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Desktop (Electron) — optional standalone installer       │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

| Layer | Tech | Purpose |
|-------|------|---------|
| Frontend | React 18 + Vite | Tool selector, upload UI, progress tracking |
| Backend | FastAPI + Uvicorn | REST API, chunked uploads, job queue |
| OCR Engine | Tesseract 5.x | Text recognition from rendered page images |
| PDF Rendering | PyMuPDF (fitz) | High-DPI page rendering, text overlay, color editing |
| PDF Processing | pikepdf (QPDF) + Pillow | Compression, image re-encoding, metadata stripping |
| Desktop | Electron 29 | Standalone Windows app with bundled backend |

---

## 🚀 Quick Start (Web)

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **Tesseract OCR** | 5.x | `winget install UB-Mannheim.TesseractOCR` (needed for OCR tool only) |

### 1. Clone & Setup Backend

```bash
git clone https://github.com/stranger0407/pdf-studio.git
cd pdf-studio/backend

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # Windows
```

### 2. Start the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Start the Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

### 4. Use It

Open **http://localhost:5173** → Select a tool → Upload PDF → Process → Download.

---

## 🔧 Tools Detail

### 🔍 OCR — Make PDFs Searchable

| Preset | DPI | Speed | Best For |
|--------|-----|-------|----------|
| **Fast** | 200 | ~1x | Quick previews, drafts |
| **Standard** ⭐ | 300 | ~1.5-2x | Daily use, sharing |
| **Maximum** | 400 | ~3-4x | Archival, print-ready |

> **Standard** and **Maximum** use a text-overlay technique: invisible text composited over original images for pixel-perfect quality + full searchability.

### 📦 Compress — Reduce File Size

| Preset | Image Quality | Description |
|--------|---------------|-------------|
| **Lossless** | 100% | Recompress streams only — zero quality loss |
| **Balanced** | JPEG Q85 | Downsample >150 DPI, strip metadata |
| **Maximum** | JPEG Q60 | Aggressive downsample >120 DPI |
| **Custom** | You choose | Full control: JPEG quality (10-100), max DPI (72-600), grayscale, metadata |

> Text in PDFs is vector-based and always stays at maximum quality — only embedded images are affected by compression settings.

### 🎨 Restyle — Change PDF Colors

| Feature | Description |
|---------|-------------|
| **Text Color** | Recolor all text and fill paths using a color picker or preset swatches |
| **Background Color** | Insert a solid color behind all content on every page |
| **Live Preview** | See how your color choices look before processing |
| **Independent** | Works without OCR — directly modifies PDF content stream color operators |

> Restyle preserves text selectability and searchability. It replaces fill-color operators (`rg`, `g`, `k`) via regex in the content streams.

---

## ⚙️ Configuration

Edit `backend/.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `TESSERACT_CMD` | Auto-detected | Path to `tesseract.exe` |
| `OCR_DPI` | `300` | Render resolution for OCR |
| `OCR_LANG` | `eng` | Tesseract language pack |

---

## 📁 Project Structure

```
pdf-studio/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI routes (unified for all tools)
│   │   ├── config.py              # Settings, env vars
│   │   ├── ocr_pipeline.py        # OCR tool (render → OCR → overlay → merge)
│   │   ├── compress_pipeline.py   # Compress tool (re-encode → recompress → save)
│   │   ├── restyle_pipeline.py    # Restyle tool (color stream editing)
│   │   ├── storage.py             # Chunked upload manager
│   │   ├── jobs.py                # Background job queue
│   │   └── logging_utils.py       # Structured logging
│   ├── launcher.py                # PyInstaller entry point
│   ├── pdf_studio_backend.spec    # PyInstaller build spec
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main app with sidebar tool selector
│   │   ├── api.js                 # Backend API client
│   │   ├── icons.jsx              # SVG icon components
│   │   ├── main.jsx               # Entry point
│   │   └── styles.css             # Design system (light + dark themes)
│   ├── index.html
│   └── package.json
├── desktop/
│   ├── main.js                    # Electron main process
│   ├── preload.js                 # Context bridge
│   ├── package.json               # Electron builder config
│   └── scripts/
│       ├── dev.ps1                # Dev: Vite + Electron
│       └── build.ps1              # Build: frontend + electron-builder
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/uploads/start` | Start chunked upload |
| `PUT` | `/api/uploads/{id}/chunk?index=N` | Upload a single chunk |
| `POST` | `/api/uploads/{id}/complete` | Finalize upload |
| `POST` | `/api/jobs` | Start job (`tool`: `"ocr"`, `"compress"`, or `"restyle"`) |
| `GET` | `/api/jobs/{id}` | Job status & progress |
| `GET` | `/api/jobs/{id}/download` | Download processed PDF |
| `GET` | `/api/logs` | Application logs |

### Job Request Parameters

```json
{
  "upload_id": "string",
  "tool": "ocr | compress | restyle",
  "quality": "fast | standard | maximum",
  "compress_preset": "lossless | balanced | maximum | custom",
  "jpeg_quality": 75,
  "max_dpi": 150,
  "grayscale": false,
  "strip_metadata": true,
  "text_color": "#000000",
  "bg_color": "#FFFFFF"
}
```

---

## 👤 Author

**Raja** — [@stranger0407](https://github.com/stranger0407)

- 📧 Email: [rgjha2001@gmail.com](mailto:rgjha2001@gmail.com)
- 🐙 GitHub: [github.com/stranger0407](https://github.com/stranger0407)

---

## 📜 License

MIT — free for personal and commercial use.

---

## 🙏 Acknowledgements

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — text recognition engine
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF rendering, composition & color editing
- [pikepdf](https://github.com/pikepdf/pikepdf) — PDF compression, repair & image re-encoding
- [Pillow](https://python-pillow.org/) — image decoding, re-encoding & grayscale conversion
- [FastAPI](https://fastapi.tiangolo.com/) — backend framework
- [Vite](https://vitejs.dev/) + [React](https://react.dev/) — frontend
- [Electron](https://www.electronjs.org/) — desktop app shell
