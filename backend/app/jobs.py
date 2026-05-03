from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_settings
from .storage import ensure_dirs


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _job_path(job_id: str) -> Path:
    settings = get_settings()
    return settings.jobs_dir / f"{job_id}.json"


def _write_job(job: Dict[str, Any]) -> None:
    path = _job_path(job["job_id"])
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")


def _read_job(job_id: str) -> Dict[str, Any]:
    path = _job_path(job_id)
    if not path.exists():
        raise ValueError("job not found")
    return json.loads(path.read_text(encoding="utf-8"))


def output_path_for_job(job_id: str) -> str:
    settings = get_settings()
    return str(settings.output_dir / f"{job_id}.pdf")


def create_job(upload: Dict[str, Any], tool: str = "ocr") -> Dict[str, Any]:
    ensure_dirs()
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "tool": tool,
        "upload_id": upload["upload_id"],
        "input_path": upload["file_path"],
        "output_path": "",
        "status": "queued",
        "progress": 0,
        "message": "Queued",
        "created_at": _now(),
        "updated_at": _now(),
    }
    _write_job(job)
    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        return _read_job(job_id)
    except ValueError:
        return None


def update_job(job_id: str, **updates: Any) -> Dict[str, Any]:
    job = _read_job(job_id)
    job.update(updates)
    job["updated_at"] = _now()
    _write_job(job)
    return job
