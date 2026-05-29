# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir — backend OAE para Electron."""

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve().parent

backend_rules = ROOT / "backend" / "rules"
backend_templates = ROOT / "backend" / "templates"
project_data = ROOT / "data"

datas = [
    (str(backend_rules / "descriptions.yaml"), "backend/rules"),
    (str(backend_rules / "anomaly_catalog.yaml"), "backend/rules"),
    (str(backend_rules / "runtime_settings.json"), "backend/rules"),
    (str(backend_rules / "legenda.yaml"), "backend/rules"),
    (str(backend_rules / "grouping.py"), "backend/rules"),
    (str(backend_rules / "anomaly_parser.py"), "backend/rules"),
]

legenda_md = project_data / "legenda.md"
if legenda_md.is_file():
    datas.append((str(legenda_md), "backend/data"))

template_docx = backend_templates / "report_template.docx"
if template_docx.is_file():
    datas.append((str(template_docx), "backend/templates"))

hiddenimports = [
    "backend",
    "backend.api",
    "backend.api.server",
    "backend.api.server_desktop",
    "backend.api.workspace",
    "backend.api.serializer",
    "backend.config",
    "backend.core",
    "backend.core.runtime_settings",
    "backend.core.text_generator",
    "backend.core.parser_excel",
    "backend.core.photo_generator",
    "backend.models",
    "backend.rules",
    "backend.rules.anomaly_parser",
    "backend.rules.grouping",
    "backend.services",
    "backend.services.report_pipeline",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "starlette.routing",
    "starlette.responses",
    "starlette.middleware",
    "starlette.middleware.cors",
    "pandas",
    "openpyxl",
    "docxtpl",
    "docx",
    "PIL",
    "PIL.Image",
    "yaml",
    "multipart",
    "pydantic",
    "pydantic_core",
    "anyio",
    "sniffio",
    "httptools",
    "websockets",
    "h11",
]

a = Analysis(
    [str(ROOT / "backend" / "api" / "server_desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchvision",
        "torchaudio",
        "tensorflow",
        "pytest",
        "numba",
        "llvmlite",
        "pygame",
        "sklearn",
        "matplotlib",
        "IPython",
        "notebook",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="oae-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="oae-backend",
)
