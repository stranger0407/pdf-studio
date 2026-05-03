<div align="center">

# PDF Studio

**Your local PDF toolkit — OCR, Compress, and more. Fast, private, 100% local.**

A modular PDF processing app. All processing runs on your machine. Your files never leave your computer.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## ✨ Tools

| Tool | Description |
|------|-------------|
| **OCR** | Convert scanned PDFs into searchable documents (3 quality presets, parallel processing) |
| **Compress** | Reduce PDF file size without quality loss (handles 1 GB+, lossless) |
| *More coming…* | Merge, Split, Watermark — planned for future releases |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PDF Studio                                │
│  ┌──────────────┐      HTTP API      ┌───────────────────┐  │
│  │   React UI   │  ◄───────────────► │  FastAPI Backend   │  │
│  │  (Vite:5173) │                    │  (Uvicorn:8000)    │  │
│  │              │                    │                    │  │
│  │  ┌────────┐  │                    │  ┌──────────────┐  │  │
│  │  │ OCR    │  │                    │  │ OCR Pipeline │  │  │
│  │  │ Tool   │  │                    │  │ (Tesseract)  │  │  │
│  │  ├────────┤  │                    │  ├──────────────┤  │  │
│  │  │Compress│  │                    │  │ Compress     │  │  │
│  │  │ Tool   │  │                    │  │ Pipeline     │  │  │
│  │  └────────┘  │                    │  │ (pikepdf)    │  │  │
│  └──────────────┘                    │  └──────────────┘  │  │
│                                      └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Tech | Purpose |
|-------|------|---------|
| Frontend | React 18 + Vite | Tool selector, upload UI, progress tracking |
| Backend | FastAPI + Uvicorn | REST API, chunked uploads, job queue |
| OCR Engine | Tesseract 5.x | Text recognition from rendered page images |
| PDF Rendering | PyMuPDF (fitz) | High-DPI page rendering + text overlay |
| PDF Processing | pikepdf (QPDF) | Compression, merging, repair, linearization |

---

## 🚀 Quick Start

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

### OCR — Make PDFs Searchable

| Preset | DPI | Speed | Best For |
|--------|-----|-------|----------|
| **Fast** | 200 | ~1x | Quick previews, drafts |
| **Standard** ⭐ | 300 | ~1.5-2x | Daily use, sharing |
| **Maximum** | 400 | ~3-4x | Archival, print-ready |

> **Standard** and **Maximum** use a text-overlay technique: invisible text composited over original images for pixel-perfect quality + full searchability.

### Compress — Reduce File Size

| Preset | Quality | Description |
|--------|---------|-------------|
| **Lossless** | 100% | Recompress streams, deduplicate objects |
| **Balanced** | 100% | + Strip thumbnails & unused metadata |
| **Maximum** | 100% | All optimizations — most space saved |

Handles files up to **1 GB+** using streaming processing with pikepdf/QPDF.

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
│   │   ├── main.py              # FastAPI routes (unified for all tools)
│   │   ├── config.py            # Settings, env vars
│   │   ├── ocr_pipeline.py      # OCR tool (render → OCR → overlay → merge)
│   │   ├── compress_pipeline.py # Compression tool (recompress → dedup → save)
│   │   ├── storage.py           # Chunked upload manager
│   │   ├── jobs.py              # Background job queue
│   │   └── logging_utils.py     # Structured logging
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app with sidebar tool selector
│   │   ├── api.js               # Backend API client
│   │   ├── icons.jsx            # SVG icon components
│   │   ├── main.jsx             # Entry point
│   │   └── styles.css           # Design system (light + dark themes)
│   ├── index.html
│   └── package.json
├── .gitignore
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
| `POST` | `/api/jobs` | Start job (`tool`: "ocr" or "compress") |
| `GET` | `/api/jobs/{id}` | Job status & progress |
| `GET` | `/api/jobs/{id}/download` | Download processed PDF |
| `GET` | `/api/logs` | Application logs |

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
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF rendering & composition
- [pikepdf](https://github.com/pikepdf/pikepdf) — PDF compression, repair & merge
- [FastAPI](https://fastapi.tiangolo.com/) — backend framework
- [Vite](https://vitejs.dev/) + [React](https://react.dev/) — frontend
