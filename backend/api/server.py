"""API HTTP FastAPI para o frontend."""

from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Annotated
import yaml
from PIL import Image

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.api import workspace as ws
from backend.core.parser_images import count_image_files
from backend.api.serializer import build_analysis_payload, run_analysis_pipeline
from backend.core.photo_layout import LayoutMaterializationError
from backend.config import DEFAULT_DESCRIPTIONS, DEFAULT_TEMPLATE
from backend.core.runtime_settings import (
    DEFAULT_RUNTIME_SETTINGS,
    load_runtime_settings,
    render_template,
    save_runtime_settings,
)
from backend.api import management_service as mgmt
from backend.api.management_schemas import (
    AnomalyCatalogPayload,
    CatalogPreviewPayload,
    DescriptionPreviewPayload,
    LegendaPayload,
)
from backend.services.report_pipeline import ReportConfig, generate_report

logger = logging.getLogger(__name__)

app = FastAPI(title="OAE Report Generator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PhotoLayoutItem(BaseModel):
    anomaly_id: str
    source_anomaly_id: str | None = None
    row_index: int | None = None
    selected_photo: str | None = None
    legend: str | None = None


class ProjectPayload(BaseModel):
    name: str = ""
    rodovia: str = ""
    km: str = ""
    bridge_id: str = ""
    photo_km: str = ""
    photo_direction: str = "S"
    bridge_location_line: str = "Ponte — BR —  — Km —"
    title: str = "Relatório de Inspeção OAE"
    selected_photos: dict[str, str] = {}
    photo_layout: list[PhotoLayoutItem] = Field(default_factory=list)
    output_dir: str | None = None


REFERENCE_FIELDS: list[dict[str, str]] = mgmt.DESCRIPTION_TEMPLATE_TOKENS


class ManagementSettingsPayload(BaseModel):
    runtime_settings: dict[str, str]
    description_rules: list[dict[str, str]]


class GenerateResponse(BaseModel):
    report_path: str
    report_download_url: str
    output_download_url: str
    photos_download_url: str
    published_output_dir: str | None = None
    published_photos_dir: str | None = None
    stats: dict
    logs: list[dict]
    steps: list[dict]


def _find_image_in_dir(directory: Path, safe_name: str) -> Path | None:
    if not directory.is_dir():
        return None
    direct = directory / safe_name
    if direct.is_file():
        return direct
    matches = [p for p in directory.rglob(safe_name) if p.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _resolve_image(project_id: str, filename: str) -> Path:
    safe_name = Path(filename).name
    for base in (
        ws.preview_dir(project_id),
        ws.images_dir(project_id),
        ws.photos_output_dir(project_id),
    ):
        if not base:
            continue
        found = _find_image_in_dir(base, safe_name)
        if found:
            return found
    raise HTTPException(status_code=404, detail=f"Imagem não encontrada: {safe_name}")


def _thumbnail_path(project_id: str, original: Path, size: int) -> Path:
    thumbs = ws.thumbs_dir(project_id)
    thumbs.mkdir(parents=True, exist_ok=True)
    return thumbs / f"{original.stem}_{size}.jpg"


def _get_or_create_thumbnail(project_id: str, original: Path, size: int) -> Path:
    thumb = _thumbnail_path(project_id, original, size)
    if thumb.is_file() and thumb.stat().st_mtime >= original.stat().st_mtime:
        return thumb
    with Image.open(original) as img:
        img = img.convert("RGB")
        img.thumbnail((size, size))
        img.save(thumb, format="JPEG", quality=80, optimize=True)
    return thumb


def _zip_directory(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if directory.is_dir():
            for file_path in sorted(directory.rglob("*")):
                if file_path.is_file():
                    arcname = file_path.relative_to(directory).as_posix()
                    zf.write(file_path, arcname)
    buffer.seek(0)
    return buffer.getvalue()


def _safe_user_output_dir(raw: str | None) -> Path | None:
    if not raw or not str(raw).strip():
        return None
    try:
        dest = Path(str(raw).strip()).expanduser()
        if not dest.is_absolute():
            return None
        dest = dest.resolve()
    except OSError:
        return None
    if not dest.is_dir():
        return None
    return dest


def _require_uploaded(project_id: str) -> None:
    if not ws.excel_path(project_id).is_file():
        raise HTTPException(status_code=400, detail="Planilha Excel não enviada.")
    images_dir = ws.images_dir(project_id)
    if count_image_files(images_dir) == 0:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma imagem encontrada na pasta enviada.",
        )


def _read_descriptions_yaml() -> str:
    if not DEFAULT_DESCRIPTIONS.is_file():
        return ""
    return DEFAULT_DESCRIPTIONS.read_text(encoding="utf-8")


def _read_description_rules() -> list[dict[str, str]]:
    return mgmt.read_description_rules()


def _write_description_rules(rules: list[dict[str, str]]) -> str:
    return mgmt.write_description_rules(rules)


def _project_text_context(payload: ProjectPayload) -> dict[str, str]:
    return {
        "project_name": payload.name.strip() or (payload.bridge_id.strip() or "OAE"),
        "rodovia": payload.rodovia.strip() or "BR",
        "km": payload.km.strip() or "—",
        "bridge_id": payload.bridge_id.strip() or "OAE",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/management/settings")
def get_management_settings() -> dict[str, object]:
    rules = _read_description_rules()
    return {
        "runtime_settings": load_runtime_settings(),
        "runtime_defaults": DEFAULT_RUNTIME_SETTINGS,
        "description_rules": rules,
        "reference_fields": REFERENCE_FIELDS,
        "anomaly_options": [r["key"] for r in rules if r["key"] != "default"],
    }


@app.put("/api/management/settings")
def update_management_settings(payload: ManagementSettingsPayload) -> dict[str, object]:
    if not payload.description_rules:
        raise HTTPException(status_code=400, detail="Inclua ao menos uma regra de descrição.")

    rule_errors = mgmt.validate_description_rules(payload.description_rules)
    if rule_errors:
        raise HTTPException(status_code=400, detail=rule_errors[0])

    try:
        generated_yaml = _write_description_rules(payload.description_rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    merged = save_runtime_settings(payload.runtime_settings)
    return {
        "status": "ok",
        "runtime_settings": merged,
        "runtime_defaults": DEFAULT_RUNTIME_SETTINGS,
        "description_rules": _read_description_rules(),
        "reference_fields": REFERENCE_FIELDS,
        "anomaly_options": [r["key"] for r in _read_description_rules() if r["key"] != "default"],
        "descriptions_yaml": generated_yaml,
    }


@app.get("/api/management/input-schema")
def get_input_schema() -> dict[str, object]:
    return mgmt.get_input_schema().model_dump()


@app.post("/api/management/validate-excel")
async def validate_excel(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Envie um arquivo Excel (.xlsx).")
    content = await file.read()
    return mgmt.validate_excel_upload(content).model_dump()


@app.get("/api/management/anomaly-catalog")
def get_anomaly_catalog() -> dict[str, object]:
    return mgmt.read_anomaly_catalog().model_dump()


@app.put("/api/management/anomaly-catalog")
def put_anomaly_catalog(payload: AnomalyCatalogPayload) -> dict[str, object]:
    try:
        return mgmt.write_anomaly_catalog(payload).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/management/anomaly-catalog/preview")
def preview_anomaly_catalog(payload: CatalogPreviewPayload) -> dict[str, object]:
    return mgmt.preview_catalog_match(payload.anomaly_text).model_dump()


@app.get("/api/management/legenda")
def get_legenda() -> dict[str, object]:
    return mgmt.read_legenda().model_dump()


@app.put("/api/management/legenda")
def put_legenda(payload: LegendaPayload) -> dict[str, object]:
    try:
        return mgmt.write_legenda(payload).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/management/preview-description")
def preview_description(payload: DescriptionPreviewPayload) -> dict[str, object]:
    return mgmt.preview_description(payload.template, payload.sample_row).model_dump()


@app.get("/api/management/photo-sections")
def get_photo_sections() -> list[dict[str, object]]:
    return [item.model_dump() for item in mgmt.get_photo_sections()]


@app.get("/api/management/summary")
def get_management_summary() -> dict[str, object]:
    return mgmt.get_management_summary().model_dump()


@app.get("/api/management/export")
def export_management_config() -> dict[str, object]:
    return mgmt.build_export_bundle().model_dump()


@app.put("/api/management/import")
async def import_management_config(request: Request) -> dict[str, str]:
    try:
        data = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="JSON inválido.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="JSON deve ser um objeto.")
    try:
        mgmt.import_config_bundle(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/api/projects/{project_id}/upload")
async def upload_project_files(
    project_id: str,
    excel: Annotated[UploadFile | None, File()] = None,
    images: list[UploadFile] = File(default=[]),
    relative_paths: list[str] = Form(default=[]),
) -> dict[str, str | int]:
    ws.ensure_workspace(project_id)
    uploaded_images = 0

    if excel and excel.filename:
        content = await excel.read()
        ws.excel_path(project_id).write_bytes(content)
        logger.info("Excel recebido para %s (%d bytes)", project_id, len(content))

    if images:
        ws.clear_images(project_id)
        img_dir = ws.images_dir(project_id)
        paths = relative_paths or []
        for index, upload in enumerate(images):
            if not upload.filename:
                continue
            rel = paths[index] if index < len(paths) else upload.filename
            rel = rel.replace("\\", "/").lstrip("/")
            parts = [p for p in rel.split("/") if p and p not in (".", "..")]
            dest = img_dir.joinpath(*parts) if parts else img_dir / upload.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(await upload.read())
            uploaded_images += 1

    images_on_disk = count_image_files(ws.images_dir(project_id))
    return {
        "status": "ok",
        "excel": ws.excel_path(project_id).name if ws.excel_path(project_id).is_file() else "",
        "images_count": images_on_disk,
    }


@app.post("/api/projects/{project_id}/upload-template")
async def upload_custom_template(
    project_id: str,
    template: Annotated[UploadFile, File()],
) -> dict[str, str]:
    ws.ensure_workspace(project_id)
    content = await template.read()
    ws.custom_template_path(project_id).write_bytes(content)
    return {"status": "ok", "name": template.filename or "custom_template.docx"}


def _request_api_base(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/api"


@app.post("/api/projects/{project_id}/analyze")
def analyze_project(project_id: str, payload: ProjectPayload, request: Request) -> dict:
    _require_uploaded(project_id)
    ws.ensure_workspace(project_id)

    preview = ws.preview_dir(project_id)
    if preview.exists():
        import shutil

        shutil.rmtree(preview)
    preview.mkdir(parents=True, exist_ok=True)

    runtime_settings = load_runtime_settings()
    text_context = _project_text_context(payload)
    location_line = render_template(
        runtime_settings.get(
            "bridge_location_line_template",
            "{project_name} — {rodovia} — — Km {km} —",
        ),
        text_context,
        fallback="{project_name} — {rodovia} — — Km {km} —",
    )

    report, groups, entries, photo_code_map, issues = run_analysis_pipeline(
        excel=ws.excel_path(project_id),
        images=ws.images_dir(project_id),
        staging_dir=preview,
        bridge_id=payload.bridge_id or None,
        photo_km=payload.photo_km or None,
        photo_direction=payload.photo_direction,
        bridge_location_line=location_line,
    )

    return build_analysis_payload(
        report=report,
        groups=groups,
        photo_entries=entries,
        photo_code_map=photo_code_map,
        issues=issues,
        project_id=project_id,
        api_base=_request_api_base(request),
    )


@app.post("/api/projects/{project_id}/generate")
def generate_project_report(project_id: str, payload: ProjectPayload) -> GenerateResponse:
    _require_uploaded(project_id)
    ws.ensure_workspace(project_id)

    template = ws.custom_template_path(project_id)
    if not template.is_file():
        template = DEFAULT_TEMPLATE

    out_dir = ws.output_dir(project_id)
    import shutil

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    runtime_settings = load_runtime_settings()
    text_context = _project_text_context(payload)
    location_line = render_template(
        runtime_settings.get(
            "bridge_location_line_template",
            "{project_name} — {rodovia} — — Km {km} —",
        ),
        text_context,
        fallback="{project_name} — {rodovia} — — Km {km} —",
    )
    default_title = render_template(
        runtime_settings.get(
            "default_report_title_template",
            "Relatório de Inspeção — {project_name}",
        ),
        text_context,
        fallback="Relatório de Inspeção — {project_name}",
    )

    config = ReportConfig(
        excel_path=ws.excel_path(project_id),
        images_dir=ws.images_dir(project_id),
        template_path=template,
        output_dir=out_dir,
        bridge_id=payload.bridge_id or None,
        title=payload.title.strip() or default_title,
        bridge_location_line=location_line,
        photo_km=payload.photo_km or None,
        photo_direction=payload.photo_direction,
        selected_photos_by_id={
            key: str(value).strip()
            for key, value in (payload.selected_photos or {}).items()
            if str(value).strip()
        },
        photo_layout=[item.model_dump() for item in payload.photo_layout]
        if payload.photo_layout
        else None,
    )

    try:
        result = generate_report(config)
    except LayoutMaterializationError as exc:
        logger.warning("Layout fotográfico rejeitado para %s: %s", project_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao gerar relatório para %s", project_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_path = str(result.output_path.resolve())
    published_output_dir: str | None = None
    published_photos_dir: str | None = None
    user_output = _safe_user_output_dir(payload.output_dir)
    if user_output:
        try:
            published = ws.publish_to_user_output(out_dir, user_output)
            published_output_dir = published.get("output_dir") or None
            published_photos_dir = published.get("photos_dir") or None
            if published.get("report_path"):
                report_path = published["report_path"]
            logger.info(
                "Relatório publicado em %s (fotos: %s)",
                published_output_dir,
                published_photos_dir,
            )
        except OSError as exc:
            logger.exception("Falha ao publicar relatório em %s", user_output)
            raise HTTPException(
                status_code=500,
                detail=f"Não foi possível gravar na pasta de saída: {exc}",
            ) from exc

    photo_count = result.report.photo_report.total_photos if result.report.photo_report else 0
    anomaly_count = len(result.report.anomalies)
    page_count = max(1, (photo_count + 1) // 2 + 10)

    base = f"/api/projects/{project_id}/artifacts"
    logs = [
        {"level": "ok", "message": f"Planilha carregada — {anomaly_count} anomalia(s)"},
        {
            "level": "ok",
            "message": f"Imagens organizadas — {photo_count} foto(s) em fotos_relatorio",
        },
        {
            "level": "ok",
            "message": f"Descrições geradas — {len(result.report.groups)} grupo(s) de anomalias",
        },
        {"level": "ok", "message": "Template Word aplicado com placeholders docxtpl"},
        {"level": "ok", "messageLogged": "Layout 2 fotos/página aplicado no anexo fotográfico"},
        {
            "level": "ok",
            "message": f"Relatório exportado: {result.output_path.name}",
        },
    ]
    # fix typo in logs
    logs[4] = {"level": "ok", "message": "Layout 2 fotos/página aplicado no anexo fotográfico"}

    steps = [
        {"id": "excel", "label": "Leitura da planilha", "status": "done"},
        {"id": "photos", "label": "Organização das fotos", "status": "done"},
        {"id": "descriptions", "label": "Geração das descrições", "status": "done"},
        {"id": "template", "label": "Inserção no template", "status": "done"},
        {"id": "pagination", "label": "Paginação", "status": "done"},
        {"id": "export", "label": "Exportação DOCX", "status": "done"},
    ]

    return GenerateResponse(
        report_path=report_path,
        report_download_url=f"{base}/report",
        output_download_url=f"{base}/output.zip",
        photos_download_url=f"{base}/photos.zip",
        published_output_dir=published_output_dir,
        published_photos_dir=published_photos_dir,
        stats={
            "pageCount": page_count,
            "photoCount": photo_count,
            "anomalyCount": anomaly_count,
            "elapsedSeconds": round(result.elapsed_seconds, 2),
            "warnings": result.warnings,
            "errors": result.errors,
        },
        logs=logs,
        steps=steps,
    )


@app.get("/api/projects/{project_id}/images/{filename}")
def get_project_image(
    project_id: str,
    filename: str,
    thumb: bool = Query(default=False),
    size: int = Query(default=320, ge=64, le=1024),
) -> FileResponse:
    path = _resolve_image(project_id, filename)
    if thumb:
        path = _get_or_create_thumbnail(project_id, path, size)
    return FileResponse(path)


@app.get("/api/projects/{project_id}/artifacts/report")
def download_report(project_id: str) -> FileResponse:
    docx = ws.find_report_docx(project_id)
    if not docx:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return FileResponse(
        docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx.name,
    )


@app.get("/api/projects/{project_id}/artifacts/output.zip")
def download_output_zip(project_id: str) -> StreamingResponse:
    out = ws.output_dir(project_id)
    if not out.is_dir() or not any(out.iterdir()):
        raise HTTPException(status_code=404, detail="Pasta de saída vazia.")
    data = _zip_directory(out)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{project_id}_output.zip"',
            "Content-Length": str(len(data)),
        },
    )


@app.get("/api/projects/{project_id}/artifacts/photos.zip")
def download_photos_zip(project_id: str) -> StreamingResponse:
    photos = ws.photos_output_dir(project_id)
    if not photos or not any(photos.iterdir()):
        raise HTTPException(status_code=404, detail="Pasta de fotos do relatório não encontrada.")
    data = _zip_directory(photos)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{project_id}_fotos_relatorio.zip"',
            "Content-Length": str(len(data)),
        },
    )


