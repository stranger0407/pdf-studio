from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_settings


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dirs() -> None:
    settings = get_settings()
    for path in [
        settings.data_dir,
        settings.upload_dir,
        settings.output_dir,
        settings.jobs_dir,
        settings.chunks_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _meta_path(upload_id: str) -> Path:
    settings = get_settings()
    return settings.upload_dir / f"{upload_id}.json"


def _part_path(upload_id: str) -> Path:
    settings = get_settings()
    return settings.upload_dir / f"{upload_id}.part"


def _final_path(upload_id: str) -> Path:
    settings = get_settings()
    return settings.upload_dir / f"{upload_id}.pdf"


def _read_meta(upload_id: str) -> Dict[str, Any]:
    path = _meta_path(upload_id)
    if not path.exists():
        raise ValueError("upload not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_meta(meta: Dict[str, Any]) -> None:
    path = _meta_path(meta["upload_id"])
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def start_upload(filename: str, total_size: int, chunk_size: int) -> Dict[str, Any]:
    ensure_dirs()
    upload_id = uuid.uuid4().hex
    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "total_size": total_size,
        "chunk_size": chunk_size,
        "received": 0,
        "next_index": 0,
        "status": "uploading",
        "created_at": _now(),
        "updated_at": _now(),
        "file_path": "",
    }
    _write_meta(meta)
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "filename": filename,
    }


def write_chunk(upload_id: str, index: int, data: bytes) -> None:
    meta = _read_meta(upload_id)
    if meta["status"] != "uploading":
        raise ValueError("upload is not accepting chunks")
    if index != meta["next_index"]:
        raise ValueError("chunk out of order")

    part_path = _part_path(upload_id)
    with part_path.open("ab") as handle:
        handle.write(data)

    meta["received"] += len(data)
    meta["next_index"] += 1
    meta["updated_at"] = _now()
    _write_meta(meta)


def complete_upload(upload_id: str) -> Dict[str, Any]:
    meta = _read_meta(upload_id)
    if meta["status"] != "uploading":
        raise ValueError("upload already completed")

    part_path = _part_path(upload_id)
    if not part_path.exists():
        raise ValueError("missing upload data")

    if meta["total_size"] and meta["received"] != meta["total_size"]:
        raise ValueError("upload size mismatch")

    final_path = _final_path(upload_id)
    part_path.replace(final_path)

    meta["status"] = "completed"
    meta["file_path"] = str(final_path)
    meta["updated_at"] = _now()
    _write_meta(meta)
    return meta


def get_upload(upload_id: str) -> Optional[Dict[str, Any]]:
    try:
        return _read_meta(upload_id)
    except ValueError:
        return None
