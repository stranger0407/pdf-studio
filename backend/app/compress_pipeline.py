"""
PDF Compression Pipeline — Professional Grade
===============================================

Handles ALL image types including DCTDecode (already-JPEG) images.
For JPEG images: reads raw JPEG bytes → Pillow → re-encodes at lower quality.
For raw images: decodes pixels → Pillow → encodes as JPEG.

Three modes:
  Lossless   — stream recompression only (fast, ~5-15%)
  Balanced   — re-encode JPEG at Q85, downsample >150 DPI (~25-50%)
  Maximum    — re-encode JPEG at Q60, downsample >120 DPI (~50-75%)
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

import pikepdf
from PIL import Image

from .logging_utils import append_log


COMPRESS_PRESETS = {
    "lossless": {
        "label": "Lossless",
        "jpeg_quality": None,
        "max_dpi": None,
        "strip_metadata": False,
    },
    "balanced": {
        "label": "Balanced",
        "jpeg_quality": 85,
        "max_dpi": 150,
        "strip_metadata": True,
    },
    "maximum": {
        "label": "Maximum",
        "jpeg_quality": 60,
        "max_dpi": 120,
        "strip_metadata": True,
    },
}


def _fmt(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _strip_thumbnails(pdf: pikepdf.Pdf) -> int:
    removed = 0
    for page in pdf.pages:
        if "/Thumb" in page:
            del page["/Thumb"]
            removed += 1
    return removed


def _strip_document_metadata(pdf: pikepdf.Pdf) -> None:
    if "/Info" in pdf.trailer:
        info = pdf.trailer["/Info"]
        if isinstance(info, pikepdf.Dictionary):
            keep = {"/Title", "/Author", "/Subject", "/Keywords"}
            for k in [k for k in info.keys() if k not in keep]:
                try:
                    del info[k]
                except Exception:
                    pass


def _get_page_dimensions_pts(page: pikepdf.Page):
    """Return (width_pts, height_pts) of a page, or None."""
    try:
        mb = page.mediabox
        if mb:
            return float(mb[2]) - float(mb[0]), float(mb[3]) - float(mb[1])
    except Exception:
        pass
    return None


def _estimate_dpi(img_w: int, img_h: int, page_dims):
    """Estimate image DPI from page dimensions."""
    if not page_dims:
        return 300  # assume 300 if unknown
    pw, ph = page_dims
    if pw <= 0 or ph <= 0:
        return 300
    dpi_x = img_w / (pw / 72)
    dpi_y = img_h / (ph / 72)
    return max(dpi_x, dpi_y)


def _compress_jpeg_image(
    xobj: pikepdf.Stream,
    pdf: pikepdf.Pdf,
    jpeg_quality: int,
    max_dpi: int | None,
    page_dims,
) -> pikepdf.Stream | None:
    """
    Compress a DCTDecode (JPEG) image by reading raw JPEG bytes,
    decoding with Pillow, optionally downsampling, and re-encoding.
    Returns new stream if smaller, None otherwise.
    """
    w = int(xobj.get("/Width", 0))
    h = int(xobj.get("/Height", 0))
    if w < 10 or h < 10:
        return None

    # Read the raw JPEG bytes directly — no pixel decompression needed
    raw_jpeg = xobj.read_raw_bytes()
    original_size = len(raw_jpeg)
    if original_size < 5000:
        return None

    try:
        img = Image.open(io.BytesIO(raw_jpeg))
        img.load()  # Force decode
    except Exception:
        return None

    # Downsample if above max DPI
    new_w, new_h = img.size
    if max_dpi and w > 100 and h > 100:
        current_dpi = _estimate_dpi(w, h, page_dims)
        if current_dpi > max_dpi * 1.1:
            scale = max_dpi / current_dpi
            new_w = max(int(new_w * scale), 10)
            new_h = max(int(new_h * scale), 10)
            img = img.resize((new_w, new_h), Image.LANCZOS)

    # Convert to RGB if needed (CMYK, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Re-encode
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
    new_data = buf.getvalue()

    # Only replace if meaningful savings (at least 5%)
    if len(new_data) >= original_size * 0.95:
        return None

    # Build replacement stream
    cs = pikepdf.Name.DeviceRGB if img.mode == "RGB" else pikepdf.Name.DeviceGray
    new_stream = pikepdf.Stream(pdf, new_data)
    new_stream["/Type"] = pikepdf.Name.XObject
    new_stream["/Subtype"] = pikepdf.Name.Image
    new_stream["/Width"] = new_w
    new_stream["/Height"] = new_h
    new_stream["/ColorSpace"] = cs
    new_stream["/BitsPerComponent"] = 8
    new_stream["/Filter"] = pikepdf.Name.DCTDecode
    return new_stream


def _compress_raw_image(
    xobj: pikepdf.Stream,
    pdf: pikepdf.Pdf,
    jpeg_quality: int,
    max_dpi: int | None,
    page_dims,
) -> pikepdf.Stream | None:
    """
    Compress a non-JPEG image (FlateDecode, raw) by decoding pixels,
    then encoding as JPEG.
    """
    w = int(xobj.get("/Width", 0))
    h = int(xobj.get("/Height", 0))
    bpc = int(xobj.get("/BitsPerComponent", 8))
    if w < 10 or h < 10 or bpc == 1:
        return None

    original_size = len(xobj.read_raw_bytes())
    if original_size < 5000:
        return None

    # Skip images with masks (need transparency)
    if "/SMask" in xobj or "/Mask" in xobj:
        return None

    # Determine color mode from colorspace
    cs = xobj.get("/ColorSpace")
    cs_str = str(cs) if cs else ""

    if isinstance(cs, pikepdf.Array) and len(cs) >= 2:
        tag = str(cs[0])
        if "ICCBased" in tag:
            icc = cs[1]
            if isinstance(icc, pikepdf.Stream):
                n = int(icc.get("/N", 3))
                if n == 1:
                    mode, channels = "L", 1
                elif n == 4:
                    mode, channels = "CMYK", 4
                else:
                    mode, channels = "RGB", 3
            else:
                mode, channels = "RGB", 3
        elif "Indexed" in tag or "Separation" in tag:
            return None  # Skip complex colorspaces
        else:
            mode, channels = "RGB", 3
    elif "RGB" in cs_str:
        mode, channels = "RGB", 3
    elif "Gray" in cs_str:
        mode, channels = "L", 1
    elif "CMYK" in cs_str:
        mode, channels = "CMYK", 4
    else:
        return None

    try:
        raw = xobj.read_bytes()
        expected = w * h * channels
        if len(raw) < expected:
            return None
        img = Image.frombytes(mode, (w, h), raw[:expected])
    except Exception:
        return None

    # Downsample
    new_w, new_h = w, h
    if max_dpi and w > 100 and h > 100:
        current_dpi = _estimate_dpi(w, h, page_dims)
        if current_dpi > max_dpi * 1.1:
            scale = max_dpi / current_dpi
            new_w = max(int(w * scale), 10)
            new_h = max(int(h * scale), 10)
            img = img.resize((new_w, new_h), Image.LANCZOS)

    if mode == "CMYK":
        img = img.convert("RGB")
        mode = "RGB"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
    new_data = buf.getvalue()

    if len(new_data) >= original_size * 0.95:
        return None

    cs_name = pikepdf.Name.DeviceRGB if mode == "RGB" else pikepdf.Name.DeviceGray
    new_stream = pikepdf.Stream(pdf, new_data)
    new_stream["/Type"] = pikepdf.Name.XObject
    new_stream["/Subtype"] = pikepdf.Name.Image
    new_stream["/Width"] = new_w
    new_stream["/Height"] = new_h
    new_stream["/ColorSpace"] = cs_name
    new_stream["/BitsPerComponent"] = 8
    new_stream["/Filter"] = pikepdf.Name.DCTDecode
    return new_stream


def _collect_all_image_refs(pdf: pikepdf.Pdf):
    """
    Collect ALL unique image object references across the entire PDF.
    This avoids processing the same shared image multiple times.
    Returns dict of obj_id -> (xobj_ref, first_page_num, page_dims)
    """
    seen = {}
    for pg_num, page in enumerate(pdf.pages):
        if "/Resources" not in page:
            continue
        res = page["/Resources"]
        if "/XObject" not in res:
            continue
        xobjects = res["/XObject"]
        if not isinstance(xobjects, pikepdf.Dictionary):
            continue

        page_dims = _get_page_dimensions_pts(page)

        for name in list(xobjects.keys()):
            xobj = xobjects[name]
            if not isinstance(xobj, pikepdf.Stream):
                continue
            if xobj.get("/Subtype") != pikepdf.Name.Image:
                continue

            # Use pikepdf object ID to deduplicate
            obj_id = xobj.objgen
            if obj_id not in seen:
                seen[obj_id] = (xobj, pg_num, page_dims)

    return seen


def process_pdf_compress(
    input_pdf: str,
    output_pdf: str,
    job_id: str,
    update_cb: Callable,
    preset: str = "lossless",
) -> None:
    _start = time.time()
    config = COMPRESS_PRESETS.get(preset, COMPRESS_PRESETS["lossless"])
    input_size = os.path.getsize(input_pdf)
    jpeg_quality = config["jpeg_quality"]
    max_dpi = config["max_dpi"]
    do_images = jpeg_quality is not None

    append_log("INFO", "compress",
               f"Start: {_fmt(input_size)}, preset={preset}, Q={jpeg_quality}, DPI={max_dpi}",
               job_id=job_id)
    update_cb(message=f"Opening PDF ({_fmt(input_size)})…", progress=2)

    tmp_dir = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="compress_"))

        # Step 1 — Open
        update_cb(message="Analyzing PDF structure…", progress=5)
        pdf = pikepdf.Pdf.open(input_pdf)
        total_pages = len(pdf.pages)
        update_cb(message=f"{total_pages} pages — scanning images…", progress=8)

        # Step 2 — Strip metadata
        if config["strip_metadata"]:
            update_cb(message="Stripping thumbnails & metadata…", progress=10)
            _strip_thumbnails(pdf)
            _strip_document_metadata(pdf)

        # Step 3 — Compress images
        total_compressed = 0
        total_saved_bytes = 0

        if do_images:
            # Collect unique images across entire PDF
            update_cb(message="Indexing unique images…", progress=12)
            unique_images = _collect_all_image_refs(pdf)
            total_unique = len(unique_images)
            append_log("INFO", "compress",
                       f"Found {total_unique} unique images across {total_pages} pages",
                       job_id=job_id)
            update_cb(message=f"Found {total_unique} unique images to process", progress=15)

            processed = 0
            for obj_id, (xobj, pg_num, page_dims) in unique_images.items():
                processed += 1

                # Determine if this is already JPEG
                filt = xobj.get("/Filter")
                is_jpeg = filt == pikepdf.Name.DCTDecode

                old_size = len(xobj.read_raw_bytes())
                new_stream = None

                try:
                    if is_jpeg:
                        new_stream = _compress_jpeg_image(
                            xobj, pdf, jpeg_quality, max_dpi, page_dims
                        )
                    else:
                        new_stream = _compress_raw_image(
                            xobj, pdf, jpeg_quality, max_dpi, page_dims
                        )
                except Exception:
                    pass

                if new_stream is not None:
                    new_size = len(new_stream.read_raw_bytes())
                    saved = old_size - new_size

                    # Replace the stream data in-place on the original object
                    xobj.write(new_stream.read_raw_bytes())
                    # Update stream dictionary
                    xobj["/Width"] = new_stream["/Width"]
                    xobj["/Height"] = new_stream["/Height"]
                    xobj["/ColorSpace"] = new_stream["/ColorSpace"]
                    xobj["/BitsPerComponent"] = 8
                    xobj["/Filter"] = pikepdf.Name.DCTDecode
                    # Remove old decode params
                    for key in ["/DecodeParms", "/Decode"]:
                        if key in xobj:
                            del xobj[key]

                    total_compressed += 1
                    total_saved_bytes += saved

                # Progress: 15% → 80%
                if processed % 10 == 0 or processed == total_unique:
                    pct = 15 + int(65 * processed / total_unique)
                    update_cb(
                        message=f"Compressing image {processed}/{total_unique} "
                                f"({total_compressed} optimized, saved {_fmt(total_saved_bytes)})",
                        progress=pct,
                    )

            append_log("INFO", "compress",
                       f"Compressed {total_compressed}/{total_unique} images, "
                       f"saved ~{_fmt(total_saved_bytes)} from images alone",
                       job_id=job_id)
        else:
            update_cb(message="Lossless mode — skipping image re-encoding", progress=15)

        # Step 4 — Save
        progress_base = 80 if do_images else 20
        is_large = input_size > 50 * 1024 * 1024

        save_kwargs = {
            "compress_streams": True,
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        }
        if not is_large:
            save_kwargs["recompress_flate"] = True
            save_kwargs["linearize"] = True

        update_cb(message="Writing compressed PDF…", progress=progress_base + 5)
        tmp_output = tmp_dir / "compressed.pdf"
        pdf.save(str(tmp_output), **save_kwargs)
        pdf.close()

        update_cb(message="Finalizing…", progress=95)
        shutil.move(str(tmp_output), output_pdf)

        # Step 5 — Report
        output_size = os.path.getsize(output_pdf)
        reduction_pct = round((1 - output_size / input_size) * 100, 1) if input_size > 0 else 0
        elapsed = round(time.time() - _start, 1)

        msg = (f"Done — {_fmt(input_size)} → {_fmt(output_size)} "
               f"({reduction_pct}% reduction) in {elapsed}s")
        if total_compressed > 0:
            msg += f" | {total_compressed} images re-encoded"

        append_log("INFO", "compress", msg, job_id=job_id)
        update_cb(
            message=msg, progress=100,
            input_size=input_size,
            output_size=output_size,
            reduction_pct=reduction_pct,
        )

    except Exception as exc:
        append_log("ERROR", "compress", str(exc), job_id=job_id)
        raise
    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
