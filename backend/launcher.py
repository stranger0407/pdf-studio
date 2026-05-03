"""
Standalone launcher for the PDF Studio backend.

PyInstaller runs this file as __main__.  It boots uvicorn and points it
at ``app.main:app`` — the FastAPI instance — which means all the relative
imports inside the ``app`` package resolve normally.
"""
from __future__ import annotations

import sys
import os

# When frozen, _MEIPASS is the temp directory where PyInstaller extracts files.
# We add it to sys.path so that `import app.main` works.
if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    if base not in sys.path:
        sys.path.insert(0, base)

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
