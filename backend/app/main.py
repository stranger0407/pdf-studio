from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import traceback
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import get_settings
from .jobs import create_job, get_job, output_path_for_job, update_job
from .logging_utils import append_log, read_logs, get_system_info
from .ocr_pipeline import process_pdf_ocr
from .compress_pipeline import process_pdf_compress
from .restyle_pipeline import process_pdf_restyle
from .storage import complete_upload, get_upload, start_upload, write_chunk

app = FastAPI(title="PDF Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=2)


class StartUploadRequest(BaseModel):
    filename: str
    total_size: int


class StartJobRequest(BaseModel):
    upload_id: str
    tool: str = "ocr"              # "ocr", "compress", or "restyle"
    quality: str = "standard"      # OCR: "fast"/"standard"/"maximum"
    compress_preset: str = "lossless"  # Compress: "lossless"/"balanced"/"maximum"/"custom"
    # Custom compression parameters (only used when compress_preset="custom")
    jpeg_quality: Optional[int] = None     # 10–100
    max_dpi: Optional[int] = None          # 72–600, null = no downsampling
    grayscale: bool = False
    strip_metadata: bool = True
    # Restyle parameters
    text_color: Optional[str] = None       # hex e.g. "#FF0000"
    bg_color: Optional[str] = None         # hex e.g. "#FFFFF0"


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/uploads/start")
def api_start_upload(request: StartUploadRequest) -> dict:
    settings = get_settings()
    if not request.filename:
        raise HTTPException(status_code=400, detail="filename required")
    if request.total_size <= 0:
        raise HTTPException(status_code=400, detail="total_size must be > 0")
    return start_upload(request.filename, request.total_size, settings.chunk_size_bytes)


@app.put("/api/uploads/{upload_id}/chunk")
async def api_upload_chunk(upload_id: str, request: Request, index: int) -> dict:
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="empty chunk")
    try:
        write_chunk(upload_id, index, data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"ok": True}


@app.post("/api/uploads/{upload_id}/complete")
def api_complete_upload(upload_id: str) -> dict:
    try:
        return complete_upload(upload_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/jobs")
def api_start_job(request: StartJobRequest) -> dict:
    upload = get_upload(request.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="upload not found")
    if not upload.get("file_path"):
        raise HTTPException(status_code=409, detail="upload not completed")

    tool = request.tool if request.tool in ("ocr", "compress", "restyle") else "ocr"
    job = create_job(upload, tool=tool)

    if tool == "ocr":
        quality = request.quality if request.quality in ("fast", "standard", "maximum") else "standard"
        job["quality"] = quality
        executor.submit(_run_ocr_job, job["job_id"], quality)
    elif tool == "compress":
        preset = request.compress_preset if request.compress_preset in ("lossless", "balanced", "maximum", "custom") else "lossless"
        job["compress_preset"] = preset
        custom_params = {
            "jpeg_quality": request.jpeg_quality,
            "max_dpi": request.max_dpi,
            "grayscale": request.grayscale,
            "strip_metadata": request.strip_metadata,
        }
        job["custom_params"] = custom_params
        executor.submit(_run_compress_job, job["job_id"], preset, custom_params)
    elif tool == "restyle":
        job["text_color"] = request.text_color
        job["bg_color"] = request.bg_color
        executor.submit(_run_restyle_job, job["job_id"], request.text_color, request.bg_color)

    return job


def _run_ocr_job(job_id: str, quality: str = "standard") -> None:
    job = get_job(job_id)
    if not job:
        return
    try:
        append_log("INFO", "ocr", f"Job started — input: {job['input_path']}, quality={quality}", job_id=job_id)
        update_job(job_id, status="processing", progress=1, message="Starting OCR")
        input_path = job["input_path"]
        output_path = output_path_for_job(job_id)
        process_pdf_ocr(
            input_path,
            output_path,
            job_id=job_id,
            update_cb=lambda **kwargs: update_job(job_id, **kwargs),
            quality=quality,
        )
        update_job(
            job_id,
            status="done",
            progress=100,
            message="Complete",
            output_path=output_path,
        )
        append_log("INFO", "ocr", "Job completed successfully", job_id=job_id)
    except Exception as exc:
        tb = traceback.format_exc()
        append_log("ERROR", "ocr", f"{exc}\n{tb}", job_id=job_id)
        update_job(job_id, status="error", message=str(exc))


def _run_compress_job(job_id: str, preset: str = "lossless", custom_params: dict | None = None) -> None:
    job = get_job(job_id)
    if not job:
        return
    cp = custom_params or {}
    try:
        append_log("INFO", "compress", f"Job started — input: {job['input_path']}, preset={preset}, custom={cp}", job_id=job_id)
        update_job(job_id, status="processing", progress=1, message="Starting compression")
        input_path = job["input_path"]
        output_path = output_path_for_job(job_id)
        process_pdf_compress(
            input_path,
            output_path,
            job_id=job_id,
            update_cb=lambda **kwargs: update_job(job_id, **kwargs),
            preset=preset,
            custom_jpeg_quality=cp.get("jpeg_quality"),
            custom_max_dpi=cp.get("max_dpi"),
            custom_grayscale=cp.get("grayscale", False),
            custom_strip_metadata=cp.get("strip_metadata", True),
        )
        update_job(
            job_id,
            status="done",
            progress=100,
            message="Complete",
            output_path=output_path,
        )
        append_log("INFO", "compress", "Job completed successfully", job_id=job_id)
    except Exception as exc:
        tb = traceback.format_exc()
        append_log("ERROR", "compress", f"{exc}\n{tb}", job_id=job_id)
        update_job(job_id, status="error", message=str(exc))


def _run_restyle_job(job_id: str, text_color: str | None = None, bg_color: str | None = None) -> None:
    job = get_job(job_id)
    if not job:
        return
    try:
        append_log("INFO", "restyle", f"Job started — input: {job['input_path']}, text={text_color}, bg={bg_color}", job_id=job_id)
        update_job(job_id, status="processing", progress=1, message="Starting restyle")
        input_path = job["input_path"]
        output_path = output_path_for_job(job_id)
        process_pdf_restyle(
            input_path,
            output_path,
            job_id=job_id,
            update_cb=lambda **kwargs: update_job(job_id, **kwargs),
            text_color=text_color,
            bg_color=bg_color,
        )
        update_job(
            job_id,
            status="done",
            progress=100,
            message="Complete",
            output_path=output_path,
        )
        append_log("INFO", "restyle", "Job completed successfully", job_id=job_id)
    except Exception as exc:
        tb = traceback.format_exc()
        append_log("ERROR", "restyle", f"{exc}\n{tb}", job_id=job_id)
        update_job(job_id, status="error", message=str(exc))


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/api/jobs/{job_id}/download")
def api_download_job(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="job not complete")
    output_path = job.get("output_path")
    if not output_path:
        raise HTTPException(status_code=404, detail="output missing")
    return FileResponse(
        output_path,
        filename=f"{job_id}.pdf",
        media_type="application/pdf",
    )

@app.get("/api/logs")
def api_get_logs(tail: int = 200) -> dict:
    """Return the last N log entries for the log viewer."""
    entries = read_logs(tail=min(tail, 500))
    system = get_system_info()
    return {"entries": entries, "system": system}
