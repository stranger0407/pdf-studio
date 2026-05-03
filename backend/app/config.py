from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Default Tesseract location on Windows (winget/UB-Mannheim installer)
_DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@dataclass(frozen=True)
class Settings:
    tesseract_cmd: str
    ocr_lang: str
    ocr_dpi: int
    ocr_quality: str          # "fast", "standard", or "maximum"
    chunk_size_bytes: int
    data_dir: Path
    upload_dir: Path
    output_dir: Path
    jobs_dir: Path
    chunks_dir: Path


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_data_dir() -> Path:
    app_data_dir = os.getenv("APP_DATA_DIR")
    if app_data_dir:
        return Path(app_data_dir)
    return Path(os.getenv("DATA_DIR", str(DATA_DIR)))


def get_settings() -> Settings:
    data_dir = _resolve_data_dir()
    upload_dir = Path(os.getenv("UPLOAD_DIR", str(data_dir / "uploads")))
    output_dir = Path(os.getenv("OUTPUT_DIR", str(data_dir / "outputs")))
    jobs_dir = Path(os.getenv("JOBS_DIR", str(data_dir / "jobs")))
    chunks_dir = Path(os.getenv("CHUNKS_DIR", str(data_dir / "chunks")))

    quality = os.getenv("OCR_QUALITY", "standard").strip().lower()
    if quality not in ("fast", "standard", "maximum"):
        quality = "standard"

    return Settings(
        tesseract_cmd=os.getenv("TESSERACT_CMD", _DEFAULT_TESSERACT).strip(),
        ocr_lang=os.getenv("OCR_LANG", "eng").strip(),
        ocr_dpi=_get_int("OCR_DPI", 300),
        ocr_quality=quality,
        chunk_size_bytes=_get_int("UPLOAD_CHUNK_SIZE_BYTES", 8 * 1024 * 1024),
        data_dir=data_dir,
        upload_dir=upload_dir,
        output_dir=output_dir,
        jobs_dir=jobs_dir,
        chunks_dir=chunks_dir,
    )
