"""
PDF Restyle Pipeline
====================

Changes the visual appearance of a PDF:
  - Background color: inserts a colored rectangle behind all content
  - Text color: modifies content stream color operators to recolor text

Uses PyMuPDF (fitz) — no OCR required. Preserves text selectability.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

import fitz  # PyMuPDF

from .logging_utils import append_log


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------
def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert '#RRGGBB' or 'RRGGBB' to (r, g, b) in 0.0–1.0 range."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def _fmt(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ---------------------------------------------------------------------------
# Content stream color replacement
# ---------------------------------------------------------------------------
# PDF color operators:
#   r g b rg    — set non-stroking (fill) color to RGB
#   r g b RG    — set stroking color to RGB
#   g G         — grayscale (fill / stroke)
#   r g b k     — CMYK fill
#   r g b K     — CMYK stroke
#   cs / CS     — set colorspace
#   sc / SC     — set color in current colorspace
#
# Strategy: replace ALL fill-color operators (rg, g, k, sc) with our
# target color. This recolors text, vector paths, and inline shapes.
# We leave stroking operators (RG, G, K, SC) alone by default to
# preserve outlines and borders.

_PATTERN_RG_FILL = re.compile(
    rb"(?<!\S)"                         # not preceded by non-whitespace
    rb"[\d.]+\s+[\d.]+\s+[\d.]+\s+rg"  # e.g. "0 0 0 rg"
    rb"(?!\S)"                          # not followed by non-whitespace
)

_PATTERN_G_FILL = re.compile(
    rb"(?<!\S)"
    rb"[\d.]+\s+g"                      # e.g. "0 g"
    rb"(?!\S)"
)

_PATTERN_K_FILL = re.compile(
    rb"(?<!\S)"
    rb"[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+k"  # CMYK fill
    rb"(?!\S)"
)


def _replace_fill_colors(stream: bytes, r: float, g: float, b: float) -> bytes:
    """Replace all fill-color operators in a content stream with the given RGB."""
    replacement = f"{r:.4f} {g:.4f} {b:.4f} rg".encode()

    # Replace RGB fill
    stream = _PATTERN_RG_FILL.sub(replacement, stream)
    # Replace grayscale fill
    stream = _PATTERN_G_FILL.sub(replacement, stream)
    # Replace CMYK fill
    stream = _PATTERN_K_FILL.sub(replacement, stream)

    return stream


# ---------------------------------------------------------------------------
# Background insertion
# ---------------------------------------------------------------------------
def _insert_background(page: fitz.Page, color: tuple[float, float, float]) -> None:
    """Insert a colored rectangle behind all existing content."""
    # Create the background shape
    shape = page.new_shape()
    shape.draw_rect(page.rect)
    shape.finish(color=None, fill=color, width=0)
    # Insert at the BOTTOM (overlay=False means insert before existing content)
    shape.commit(overlay=False)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def process_pdf_restyle(
    input_pdf: str,
    output_pdf: str,
    job_id: str,
    update_cb: Callable,
    text_color: str | None = None,      # hex like "#FF0000"
    bg_color: str | None = None,        # hex like "#FFFFFF"
) -> None:
    _start = time.time()
    input_size = os.path.getsize(input_pdf)

    # Parse colors
    tc = _hex_to_rgb(text_color) if text_color else None
    bc = _hex_to_rgb(bg_color) if bg_color else None

    append_log("INFO", "restyle",
               f"Start: {_fmt(input_size)}, text_color={text_color}, bg_color={bg_color}",
               job_id=job_id)
    update_cb(message=f"Opening PDF ({_fmt(input_size)})…", progress=2)

    tmp_dir = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="restyle_"))
        doc = fitz.open(input_pdf)
        total_pages = len(doc)
        update_cb(message=f"{total_pages} pages — applying style changes…", progress=5)

        for idx in range(total_pages):
            page = doc[idx]

            # --- Background color ---
            if bc:
                _insert_background(page, bc)

            # --- Text color ---
            if tc:
                # Clean and consolidate content streams first
                page.clean_contents()
                xref_list = page.get_contents()
                for xref in xref_list:
                    stream = doc.xref_stream(xref)
                    if stream:
                        new_stream = _replace_fill_colors(stream, tc[0], tc[1], tc[2])
                        if new_stream != stream:
                            doc.update_stream(xref, new_stream)

            # Progress: 5% → 85%
            if (idx + 1) % 5 == 0 or idx == total_pages - 1:
                pct = 5 + int(80 * (idx + 1) / total_pages)
                update_cb(
                    message=f"Restyled {idx + 1}/{total_pages} pages",
                    progress=pct,
                )

        # Save
        update_cb(message="Writing restyled PDF…", progress=88)
        tmp_output = tmp_dir / "restyled.pdf"
        doc.save(str(tmp_output), deflate=True, deflate_images=True, garbage=3)
        doc.close()

        update_cb(message="Finalizing…", progress=95)
        shutil.move(str(tmp_output), output_pdf)

        output_size = os.path.getsize(output_pdf)
        elapsed = round(time.time() - _start, 1)

        changes = []
        if tc:
            changes.append(f"text→{text_color}")
        if bc:
            changes.append(f"bg→{bg_color}")

        msg = (f"Done — {total_pages} pages restyled in {elapsed}s "
               f"({', '.join(changes)})")
        append_log("INFO", "restyle", msg, job_id=job_id)
        update_cb(
            message=msg, progress=100,
            input_size=input_size,
            output_size=output_size,
        )

    except Exception as exc:
        append_log("ERROR", "restyle", str(exc), job_id=job_id)
        raise
    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
