# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# All hidden imports that PyInstaller cannot auto-detect.
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "fastapi",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "pydantic",
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "anyio._backends._asyncio",
    "pytesseract",
    "fitz",
    "pymupdf",
    "pikepdf",
    "PIL",
    "PIL.Image",
    "python_dotenv",
    "dotenv",
    "multipart",
    "python_multipart",
    "email.mime.multipart",
    "concurrent.futures",
]

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[("app", "app")],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdf-studio-backend",
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="pdf-studio-backend",
)
