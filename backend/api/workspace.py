"""Gestão de workspaces por projeto (uploads e saídas)."""

from __future__ import annotations

import shutil
from pathlib import Path

from backend.config import DATA_ROOT, REPORT_PHOTOS_DIR_NAME, is_desktop_mode
from backend.config import PACKAGE_ROOT

WORKSPACES_ROOT = (DATA_ROOT / "workspaces") if is_desktop_mode() else PACKAGE_ROOT.parent / "workspaces"


def workspace_dir(project_id: str) -> Path:
    safe_id = project_id.replace("..", "").replace("/", "").replace("\\", "")
    return WORKSPACES_ROOT / safe_id


def input_dir(project_id: str) -> Path:
    return workspace_dir(project_id) / "input"


def images_dir(project_id: str) -> Path:
    return input_dir(project_id) / "images"


def excel_path(project_id: str) -> Path:
    return input_dir(project_id) / "inspection.xlsx"


def output_dir(project_id: str) -> Path:
    return workspace_dir(project_id) / "output"


def preview_dir(project_id: str) -> Path:
    return workspace_dir(project_id) / "preview"


def thumbs_dir(project_id: str) -> Path:
    return workspace_dir(project_id) / "thumbs"


def custom_template_path(project_id: str) -> Path:
    return input_dir(project_id) / "custom_template.docx"


def ensure_workspace(project_id: str) -> Path:
    root = workspace_dir(project_id)
    input_dir(project_id).mkdir(parents=True, exist_ok=True)
    images_dir(project_id).mkdir(parents=True, exist_ok=True)
    output_dir(project_id).mkdir(parents=True, exist_ok=True)
    thumbs_dir(project_id).mkdir(parents=True, exist_ok=True)
    return root


def clear_images(project_id: str) -> None:
    img = images_dir(project_id)
    if img.exists():
        shutil.rmtree(img)
    img.mkdir(parents=True, exist_ok=True)


def find_report_docx(project_id: str) -> Path | None:
    out = output_dir(project_id)
    if not out.is_dir():
        return None
    docx_files = sorted(out.glob("*_relatorio.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if docx_files:
        return docx_files[0]
    fallback = sorted(out.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return fallback[0] if fallback else None


def photos_output_dir(project_id: str) -> Path | None:
    staged = output_dir(project_id) / REPORT_PHOTOS_DIR_NAME
    return staged if staged.is_dir() else None


def publish_to_user_output(workspace_output: Path, destination: Path) -> dict[str, str]:
    """
    Copia relatório .docx e pasta fotos_relatorio para a pasta escolhida pelo usuário.
    """
    dest = destination.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    report_path = ""
    docx_files = sorted(
        workspace_output.glob("*.docx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if docx_files:
        target = dest / docx_files[0].name
        shutil.copy2(docx_files[0], target)
        report_path = str(target)

    photos_dir = ""
    staged = workspace_output / REPORT_PHOTOS_DIR_NAME
    if staged.is_dir() and any(staged.iterdir()):
        photos_dest = dest / REPORT_PHOTOS_DIR_NAME
        if photos_dest.exists():
            shutil.rmtree(photos_dest)
        shutil.copytree(staged, photos_dest)
        photos_dir = str(photos_dest)

    return {
        "output_dir": str(dest),
        "report_path": report_path,
        "photos_dir": photos_dir,
    }
