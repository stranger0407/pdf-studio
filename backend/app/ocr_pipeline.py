from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz      # PyMuPDF – renders PDF pages without Ghostscript
import pikepdf   # merge the OCR'd pages back

from .config import get_settings
from .logging_utils import append_log


# ---------------------------------------------------------------------------
# Quality presets
# ---------------------------------------------------------------------------
QUALITY_PRESETS = {
    "fast": {
        "dpi": 200,
        "psm": 6,         # uniform text block – faster, less layout analysis
        "textonly": False, # let tesseract produce its own image+text PDF
    },
    "standard": {
        "dpi": 300,
        "psm": 3,         # fully automatic page segmentation (best general quality)
        "textonly": True,  # overlay invisible text on original high-res image
    },
    "maximum": {
        "dpi": 400,
        "psm": 3,
        "textonly": True,
    },
}


# ---------------------------------------------------------------------------
# High-performance parallel OCR pipeline
# ---------------------------------------------------------------------------
# Strategy for maximum CPU utilization:
#   1. Render every page to a PNM image with PyMuPDF (fast, C-level, no GS)
#   2. Launch one `tesseract.exe` subprocess **per CPU core** concurrently
#      using raw subprocess.Popen (no pytesseract, no GIL involvement)
#   3. Each tesseract process is an independent OS process — the OS
#      scheduler distributes them across all available cores automatically
#   4. Merge the per-page PDFs with pikepdf
#
# Quality modes:
#   - "fast"     : 200 DPI, PSM 6, tesseract image+text PDF (like before)
#   - "standard" : 300 DPI, PSM 3, text-only overlay on original images
#   - "maximum"  : 400 DPI, PSM 3, text-only overlay on original images
#
# The "text-only overlay" approach is the key quality improvement:
#   Instead of Tesseract rendering a JPEG-compressed image inside the PDF
#   (which degrades quality), we:
#     a) Ask Tesseract to produce a text-only PDF (invisible text layer)
#     b) Extract that text layer and composite it on top of the original
#        high-resolution page image rendered by PyMuPDF
#   This gives pixel-perfect image quality + full searchability.
# ---------------------------------------------------------------------------


def _extract_page_images(doc: fitz.Document, tmp_dir: Path,
                         dpi: int, update_cb) -> list[Path]:
    """Render all pages to PNM files. Returns list of image paths."""
    total = len(doc)
    img_paths: list[Path] = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for idx in range(total):
        pix = doc[idx].get_pixmap(matrix=mat)
        # PNM is uncompressed — ~10x faster to save than PNG (no compression)
        img_path = tmp_dir / f"page_{idx + 1:04d}.pnm"
        pix.save(str(img_path))
        img_paths.append(img_path)

        if (idx + 1) % 10 == 0 or idx == total - 1:
            update_cb(
                message=f"Rendered {idx + 1}/{total} page images",
                progress=5 + int(15 * (idx + 1) / total),   # 5% → 20%
            )

    return img_paths


def _run_tesseract_batch(
    tesseract_cmd: str,
    lang: str,
    img_paths: list[Path],
    out_dir: Path,
    max_parallel: int,
    update_cb,
    total_pages: int,
    psm: int = 3,
    textonly: bool = False,
) -> list[Path]:
    """
    Run tesseract on many images with up to `max_parallel` concurrent
    OS-level processes. Returns list of output PDF paths (in order).
    """
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}

    # Build the base command template
    base_config = [
        "-l", lang,
        "--psm", str(psm),
        "-c", "tessedit_do_invert=0",   # skip inversion check
    ]
    if textonly:
        # Tell Tesseract to produce a text-only PDF (invisible text, no image)
        base_config.extend(["-c", "textonly_pdf=1"])

    out_pdf_paths: list[Path] = []
    for img_path in img_paths:
        # tesseract appends ".pdf" to the output base name
        out_base = out_dir / img_path.stem
        out_pdf_paths.append(Path(str(out_base) + ".pdf"))

    # ---- launch processes in sliding-window batches ----
    completed = 0
    pending: list[tuple[int, subprocess.Popen]] = []

    def _drain(wait_all: bool):
        nonlocal completed, pending
        still_running = []
        for idx, proc in pending:
            if wait_all:
                proc.wait()
            elif proc.poll() is None:
                still_running.append((idx, proc))
                continue

            if proc.returncode and proc.returncode != 0:
                stderr_out = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(
                    f"Tesseract failed on page {idx + 1} "
                    f"(exit {proc.returncode}): {stderr_out}"
                )

            completed += 1
            pct = 20 + int(60 * completed / total_pages)   # 20% → 80%
            update_cb(
                message=f"OCR processed {completed}/{total_pages} pages",
                progress=pct,
            )

        if wait_all:
            pending = []
        else:
            pending = still_running

    for i, img_path in enumerate(img_paths):
        out_base = out_dir / img_path.stem
        cmd = [
            tesseract_cmd,
            str(img_path),
            str(out_base),
            *base_config,
            "pdf",
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        pending.append((i, proc))

        # Keep at most `max_parallel` processes alive
        while len(pending) >= max_parallel:
            _drain(wait_all=False)
            if len(pending) >= max_parallel:
                # tight-poll: wait for the oldest one
                pending[0][1].wait()
                _drain(wait_all=False)

    # wait for all remaining
    _drain(wait_all=True)

    return out_pdf_paths


def _build_overlay_page(
    img_path: Path,
    text_pdf_path: Path,
    page_width: float,
    page_height: float,
) -> fitz.Document:
    """
    Build a single-page PDF with a pre-rendered image + invisible OCR text.

    Instead of re-rendering from the source PDF (expensive), this reuses the
    PNM image already rendered in step 2. This saves ~60-70% of overlay time.

    Args:
        img_path:    Path to the PNM image already rendered in step 2
        text_pdf_path: Path to Tesseract's text-only PDF for this page
        page_width:  Original page width in points
        page_height: Original page height in points

    Result: pixel-perfect image + searchable text, no JPEG artifacts.
    """
    page_rect = fitz.Rect(0, 0, page_width, page_height)

    # Load the already-rendered image (no re-render needed!)
    pix = fitz.Pixmap(str(img_path))

    # Create a new single-page document
    out_doc = fitz.open()
    new_page = out_doc.new_page(width=page_width, height=page_height)

    # Insert the image as the page background (full quality, no JPEG)
    new_page.insert_image(page_rect, pixmap=pix)

    # Open the text-only PDF from Tesseract and overlay it
    text_doc = fitz.open(str(text_pdf_path))
    if len(text_doc) > 0:
        # show_pdf_page scales the text layer to match our page rect
        new_page.show_pdf_page(page_rect, text_doc, 0)

    text_doc.close()
    return out_doc


def process_pdf_ocr(
    input_pdf: str,
    output_pdf: str,
    job_id: str,
    update_cb,
    quality: str = "standard",
) -> None:
    import time as _time
    _start = _time.time()

    settings = get_settings()
    tmp_dir = None

    # Resolve quality preset
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["standard"])
    dpi = preset["dpi"]
    psm = preset["psm"]
    textonly = preset["textonly"]

    try:
        # ------------------------------------------------------------------
        # Step 1 – Open source PDF
        # ------------------------------------------------------------------
        update_cb(message="Opening PDF…", progress=2)
        doc = fitz.open(input_pdf)
        total_pages = len(doc)

        # Save original page dimensions (needed for overlay step)
        page_sizes = [(doc[i].rect.width, doc[i].rect.height) for i in range(total_pages)]

        ncpus = os.cpu_count() or 4
        append_log("INFO", "ocr",
                   f"{total_pages} pages, {ncpus} CPU cores, DPI={dpi}, "
                   f"PSM={psm}, quality={quality}, textonly={textonly}, "
                   f"tesseract={settings.tesseract_cmd}",
                   job_id=job_id)
        update_cb(
            message=f"PDF has {total_pages} pages — using {ncpus} cores ({quality} quality)",
            progress=5,
        )

        # ------------------------------------------------------------------
        # Step 2 – Render all pages to PNM images (for Tesseract input)
        # ------------------------------------------------------------------
        tmp_dir = Path(tempfile.mkdtemp(prefix="ocr_pages_"))
        img_paths = _extract_page_images(doc, tmp_dir, dpi, update_cb)
        doc.close()
        append_log("INFO", "ocr", f"Image extraction done ({len(img_paths)} images at {dpi} DPI)", job_id=job_id)

        # ------------------------------------------------------------------
        # Step 3 – Run N tesseract processes in parallel
        # ------------------------------------------------------------------
        out_dir = tmp_dir / "out"
        out_dir.mkdir()

        pdf_paths = _run_tesseract_batch(
            tesseract_cmd=settings.tesseract_cmd,
            lang=settings.ocr_lang,
            img_paths=img_paths,
            out_dir=out_dir,
            max_parallel=ncpus,
            update_cb=update_cb,
            total_pages=total_pages,
            psm=psm,
            textonly=textonly,
        )

        # ------------------------------------------------------------------
        # Step 4 – Build the final PDF
        # ------------------------------------------------------------------
        if textonly:
            # OVERLAY MODE: Reuse step-2 images + add invisible text layer
            # No re-rendering needed — we load the PNM files from step 2
            update_cb(message="Building high-quality overlay pages…", progress=82)

            overlay_dir = tmp_dir / "overlay"
            overlay_dir.mkdir()
            overlay_paths: list[Path] = []

            for i in range(total_pages):
                pw, ph = page_sizes[i]
                overlay_doc = _build_overlay_page(img_paths[i], pdf_paths[i], pw, ph)
                overlay_path = overlay_dir / f"overlay_{i + 1:04d}.pdf"
                overlay_doc.save(str(overlay_path), deflate=True, deflate_images=True)
                overlay_doc.close()
                overlay_paths.append(overlay_path)

                if (i + 1) % 10 == 0 or i == total_pages - 1:
                    update_cb(
                        message=f"Building overlay {i + 1}/{total_pages} pages",
                        progress=82 + int(13 * (i + 1) / total_pages),  # 82% → 95%
                    )

            # Merge overlay pages
            update_cb(message="Merging pages into final PDF…", progress=96)
            merged = pikepdf.Pdf.new()
            for p in overlay_paths:
                with pikepdf.Pdf.open(p) as part:
                    merged.pages.extend(part.pages)
            merged.save(output_pdf, linearize=True)
            merged.close()
        else:
            # FAST MODE: Use Tesseract's image+text PDFs directly (like before)
            update_cb(message="Merging pages into final PDF…", progress=96)
            merged = pikepdf.Pdf.new()
            for p in pdf_paths:
                with pikepdf.Pdf.open(p) as part:
                    merged.pages.extend(part.pages)
            merged.save(output_pdf, linearize=True)
            merged.close()

        elapsed = round(_time.time() - _start, 1)
        append_log("INFO", "ocr",
                   f"OCR complete — {total_pages} pages in {elapsed}s "
                   f"({round(elapsed/total_pages, 2)} s/page, quality={quality})",
                   job_id=job_id)
        update_cb(message="Local OCR complete", progress=100)

    finally:
        if tmp_dir and Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
