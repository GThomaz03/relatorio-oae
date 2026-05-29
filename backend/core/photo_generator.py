"""Geração de relatório fotográfico e legendas."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.core.photo_numbering import PhotoAssignment
from backend.core.runtime_settings import load_runtime_settings, render_template
from backend.core.text_generator import description_body_for_anomaly
from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup, PhotoEntry, PhotoReport, PhotoSection
from backend.models.structure import parse_local_code
from backend.rules.photo_section_order import (
    photo_section_rank,
    resolve_photo_section,
    sort_anomalies_for_photo_report,
)

logger = logging.getLogger(__name__)


def _description_line(anomaly: Anomaly) -> str:
    """
    Linha descritiva do anexo fotográfico.

    Sempre baseada na anomalia individual — o agrupamento textual do relatório
    de anomalias não deve sobrescrever vão, face ou demais metadados da foto.
    """
    if anomaly.description_override and str(anomaly.description_override).strip():
        text = str(anomaly.description_override).strip()
        return text if text.endswith(".") else f"{text}."

    if anomaly.view and str(anomaly.view).strip():
        text = str(anomaly.view).strip()
        return text if text.endswith(".") else f"{text}."

    body = description_body_for_anomaly(anomaly)
    return body if body.endswith(".") else f"{body}."


def build_photo_entry(
    anomaly: Anomaly,
    image_path: str,
    sequence_index: int,
    figure_number: int,
    location_line: str,
    report_code: str | None = None,
    photo_code_map: dict[str, str] | None = None,
) -> PhotoEntry:
    code = report_code or Path(image_path).stem
    description_line = _description_line(anomaly)
    settings = load_runtime_settings()
    caption_template = settings.get(
        "photo_caption_template",
        "Fig. {figure_number} — {code} — {description_line}",
    )
    caption = render_template(
        caption_template,
        {
            "figure_number": str(figure_number),
            "code": code,
            "description_line": description_line,
            "location_line": location_line,
        },
        fallback="Fig. {figure_number} — {code} — {description_line}",
    )
    return PhotoEntry(
        image_path=image_path,
        code=code,
        location_line=location_line,
        description_line=description_line,
        caption=caption,
        anomaly_number=anomaly.number,
        anomaly_local=anomaly.local,
        anomaly_row_index=anomaly.row_index,
        sequence_index=sequence_index,
        figure_number=figure_number,
    )


def build_photo_report_from_assignments(
    assignments: list[PhotoAssignment],
    location_line: str = "Ponte — BR —  — Km —",
    photo_code_map: dict[str, str] | None = None,
) -> PhotoReport:
    """Monta anexo fotográfico na ordem documental com códigos RSP."""
    entries: list[PhotoEntry] = []
    for assignment in assignments:
        entries.append(
            build_photo_entry(
                assignment.anomaly,
                assignment.image_path,
                assignment.figure_number,
                assignment.figure_number,
                location_line,
                report_code=assignment.report_code,
                photo_code_map=photo_code_map,
            )
        )

    logger.info("Relatório fotográfico RSP: %d foto(s)", len(entries))
    return PhotoReport(ordered_entries=entries, total_photos=len(entries))


def build_photo_report(
    anomalies: list[Anomaly],
    groups: list[AnomalyGroup] | None = None,
    location_line: str = "Ponte — BR —  — Km —",
) -> PhotoReport:
    """
    Organiza sequência fotográfica para o ANEXO VI (modo legado, sem códigos RSP).

    Ordem: percorre anomalias da planilha; ordenação final por stem do ficheiro.
    """
    _ = groups
    entries: list[PhotoEntry] = []
    figure_counter = 0

    for anomaly in sort_anomalies_for_photo_report(anomalies):
        for seq_idx, image_path in enumerate(anomaly.images, start=1):
            figure_counter += 1
            entries.append(
                build_photo_entry(
                    anomaly,
                    image_path,
                    seq_idx,
                    figure_counter,
                    location_line,
                )
            )

    sections_map: dict[str, PhotoSection] = {}
    for entry in entries:
        code = parse_local_prefix(entry.anomaly_local)
        section_key = resolve_photo_section(entry.anomaly_local, code)
        if section_key not in sections_map:
            sections_map[section_key] = PhotoSection(
                section_id=section_key,
                title=f"Elemento {code}",
                entries=[],
            )
        sections_map[section_key].entries.append(entry)

    sections = sorted(
        sections_map.values(),
        key=lambda s: photo_section_rank(s.section_id),
    )
    total = len(entries)
    logger.info("Relatório fotográfico: %d foto(s)", total)
    return PhotoReport(sections=sections, ordered_entries=entries, total_photos=total)


def parse_local_prefix(local: str) -> str:
    code = parse_local_code(local)
    if code:
        return code
    letters = "".join(c for c in local if c.isalpha())
    return letters[:2].upper() if letters else "GERAL"


def flatten_photo_entries(photo_report: PhotoReport | None) -> list[PhotoEntry]:
    """Lista plana de fotos para o template Word (preserva ordem documental se RSP)."""
    if not photo_report:
        return []
    if photo_report.ordered_entries:
        return list(photo_report.ordered_entries)

    entries: list[PhotoEntry] = []
    for section in sorted(photo_report.sections, key=lambda s: photo_section_rank(s.section_id)):
        entries.extend(section.entries)
    return entries
