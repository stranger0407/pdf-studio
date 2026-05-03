from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path
from typing import Any, Dict, List

from .config import get_settings

_LOG_FILE: Path | None = None


def _log_path() -> Path:
    global _LOG_FILE
    if _LOG_FILE is None:
        settings = get_settings()
        log_dir = settings.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _LOG_FILE = log_dir / "app.log"
    return _LOG_FILE


def append_log(level: str, source: str, message: str, *, job_id: str = "") -> None:
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "level": level,
        "source": source,
        "message": message,
        "job_id": job_id,
    }
    try:
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def read_logs(tail: int = 200) -> List[Dict[str, Any]]:
    path = _log_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    result = []
    for line in lines[-tail:]:
        try:
            result.append(json.loads(line))
        except Exception:
            result.append({"ts": "", "level": "RAW", "source": "log", "message": line, "job_id": ""})
    return result


def get_system_info() -> Dict[str, Any]:
    settings = get_settings()
    tess_path = Path(settings.tesseract_cmd)
    return {
        "cpu_count": os.cpu_count() or 1,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "tesseract_cmd": settings.tesseract_cmd,
        "tesseract_exists": tess_path.exists(),
        "ocr_dpi": settings.ocr_dpi,
        "ocr_lang": settings.ocr_lang,
        "data_dir": str(settings.data_dir),
    }
