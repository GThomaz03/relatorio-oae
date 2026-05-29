"""Geração de relatório Word via docxtpl."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from backend.config import PHOTO_HEIGHT_MM, PHOTO_WIDTH_MM
from backend.core.document_structure import build_anomaly_macros
from backend.core.docx_formatting import apply_report_formatting
from backend.core.photo_generator import flatten_photo_entries
from backend.models.inspection import InspectionReport

logger = logging.getLogger(__name__)


def _safe_inline_image(doc: DocxTemplate, image_path: str) -> InlineImage | None:
    path = Path(image_path)
    if not path.is_file():
        logger.warning("Imagem ignorada na renderização Word: %s", image_path)
        return None
    try:
        return InlineImage(
            doc,
            str(path),
            width=Mm(PHOTO_WIDTH_MM),
            height=Mm(PHOTO_HEIGHT_MM),
        )
    except Exception as exc:
        logger.error("Falha ao embutir imagem %s: %s", image_path, exc)
        return None


def build_context(report: InspectionReport) -> dict[str, Any]:
    """Monta contexto Jinja2 alinhado ao modelo RSP."""
    photo_report = report.photo_report
    meta = report.metadata
    location_line = meta.bridge_location_line

    photos = [
        {
            "image_path": entry.image_path,
            "code": entry.code,
            "location_line": entry.location_line or location_line,
            "description_line": entry.description_line,
            "caption": entry.caption,
            "image": None,
        }
        for entry in flatten_photo_entries(photo_report)
    ]

    return {
        "title": meta.title,
        "bridge_id": meta.bridge_id or "OAE",
        "bridge_location_line": location_line,
        "generated_at": meta.generated_at.strftime("%d/%m/%Y %H:%M"),
        "generated_date": meta.generated_at.strftime("%d/%m/%Y"),
        "total_anomalies": len(report.anomalies),
        "total_groups": len(report.groups),
        "total_photos": photo_report.total_photos if photo_report else 0,
        "anomaly_macros": build_anomaly_macros(report.groups),
        "photos": photos,
        "sections": [],
        "groups": [
            {
                "group_id": g.group_id,
                "section_id": g.section_id,
                "description": g.description,
                "locals": ", ".join(g.locals),
                "anomaly_type": g.anomaly_type,
            }
            for g in report.groups
        ],
        "anomalies": [
            {
                "number": a.number,
                "local": a.local,
                "face": a.face,
                "anomaly_type": a.anomaly_type,
                "observations": a.observations or "",
                "image_count": len(a.images),
            }
            for a in report.anomalies
        ],
    }


def _inject_inline_images(doc: DocxTemplate, context: dict[str, Any]) -> None:
    for photo in context.get("photos", []):
        path = photo.get("image_path")
        if path:
            photo["image"] = _safe_inline_image(doc, path)


def render_report(
    report: InspectionReport,
    output_path: Path,
    template_path: Path | None = None,
) -> Path:
    """
    Renderiza template Word e exporta DOCX.

    Raises:
        FileNotFoundError: template inexistente.
    """
    template = template_path or report.metadata.template_path
    if not template.is_file():
        raise FileNotFoundError(f"Template não encontrado: {template}")

    logger.info("Gerando documento Word: %s", output_path)
    doc = DocxTemplate(str(template))
    context = build_context(report)
    _inject_inline_images(doc, context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.render(context)
    apply_report_formatting(doc.docx)
    doc.save(str(output_path))
    logger.info("Documento exportado: %s (%d bytes)", output_path, output_path.stat().st_size)
    return output_path


def default_output_filename(report: InspectionReport) -> str:
    bridge = report.metadata.bridge_id or "OAE"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_bridge = "".join(c if c.isalnum() or c in "-_" else "_" for c in bridge)
    return f"{safe_bridge}_{timestamp}_relatorio.docx"
