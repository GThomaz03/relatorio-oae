"""Pipeline reutilizável de geração de relatório OAE."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from backend.core.parser_excel import parse_excel
from backend.core.photo_generator import (
    build_photo_report,
    build_photo_report_from_assignments,
    flatten_photo_entries,
)
from backend.core.photo_numbering import assign_photo_codes, build_photo_prefix
from backend.core.report_image_staging import (
    report_photos_dir,
    rename_staged_photos_from_paths,
    rename_staged_photos_sequential,
    stage_report_images,
)
from backend.core.text_generator import build_sections, rebuild_group_descriptions
from backend.core.validators import (
    Severity,
    raise_if_blocking,
    validate_inspection,
)
from backend.core.word_generator import default_output_filename, render_report
from backend.models.inspection import InspectionReport, ReportMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportConfig:
    excel_path: Path
    images_dir: Path
    template_path: Path
    output_dir: Path
    excel_sheet: str | None = None
    bridge_id: str | None = None
    title: str = "Relatório de Inspeção OAE"
    bridge_location_line: str = "Ponte — BR —  — Km —"
    photo_km: str | None = None
    photo_direction: str = "S"
    photo_start: int = 1
    strict: bool = False
    output_filename: str | None = None
    manual_photo_tokens: dict[int, str] | None = None
    selected_photos_by_id: dict[str, str] | None = None
    photo_layout: list[dict] | None = None


@dataclass
class ReportResult:
    output_path: Path
    report: InspectionReport
    elapsed_seconds: float
    warnings: int
    errors: int
    report_photos_dir: Path | None = None
    photo_renames: dict[str, str] | None = None


def _use_rsp_photo_numbering(config: ReportConfig) -> bool:
    return bool(config.photo_km and config.bridge_id)


def generate_report(config: ReportConfig) -> ReportResult:
    """Executa o pipeline completo de geração de relatório."""
    start = time.perf_counter()
    logger.info("Iniciando pipeline de relatório OAE")

    anomalies, parse_issues = parse_excel(config.excel_path, sheet_name=config.excel_sheet)

    from backend.core.photo_layout import PhotoLayoutEntry, materialize_anomalies_from_layout

    layout_entries: list[PhotoLayoutEntry] | None = None
    if config.photo_layout:
        layout_entries = [PhotoLayoutEntry.from_dict(item) for item in config.photo_layout]

    anomalies = materialize_anomalies_from_layout(
        anomalies,
        layout_entries,
        selected_photos=config.selected_photos_by_id,
    )

    staged_dir = report_photos_dir(config.output_dir)
    anomalies, staging_issues = stage_report_images(
        anomalies,
        config.images_dir,
        staged_dir,
    )
    from backend.rules.photo_section_order import sort_anomalies_for_photo_report

    if not layout_entries:
        anomalies = sort_anomalies_for_photo_report(anomalies)

    all_parse_issues = parse_issues + staging_issues
    blocking_parse = [i for i in all_parse_issues if i.severity == Severity.ERROR]
    if blocking_parse and config.strict:
        from backend.core.validators import ImageNotFoundError

        raise ImageNotFoundError(
            blocking_parse[0].message,
            issues=blocking_parse,
        )

    metadata = ReportMetadata(
        excel_path=config.excel_path.resolve(),
        images_dir=staged_dir.resolve(),
        template_path=config.template_path.resolve(),
        bridge_id=config.bridge_id,
        title=config.title,
        bridge_location_line=config.bridge_location_line,
        photo_km=config.photo_km,
        photo_direction=config.photo_direction,
        photo_start=config.photo_start,
        source_images_dir=config.images_dir.resolve(),
        report_photos_dir=staged_dir.resolve(),
    )

    report = InspectionReport(metadata=metadata, anomalies=anomalies)
    validation_issues = validate_inspection(report, strict=config.strict)
    all_issues = all_parse_issues + validation_issues
    raise_if_blocking(all_issues, strict=config.strict)

    groups = build_sections(anomalies)
    assignments: list = []

    if _use_rsp_photo_numbering(config):
        prefix = build_photo_prefix(config.bridge_id or "", config.photo_km or "")
        from backend.core.photo_numbering import assign_photo_codes_from_anomalies

        if layout_entries:
            assignments, code_map = assign_photo_codes_from_anomalies(
                anomalies,
                groups,
                prefix,
                start=config.photo_start,
                direction=config.photo_direction,
            )
        else:
            assignments, code_map = assign_photo_codes(
                groups,
                prefix,
                start=config.photo_start,
                direction=config.photo_direction,
            )
        groups = rebuild_group_descriptions(groups, photo_code_map=code_map)
        photo_report = build_photo_report_from_assignments(
            assignments,
            location_line=config.bridge_location_line,
            photo_code_map=code_map,
        )
    else:
        if config.photo_km and not config.bridge_id:
            logger.warning(
                "photo-km ignorado: --bridge-id é necessário para códigos RSP"
            )
        elif not config.photo_km:
            logger.info("Códigos RSP desactivados (--photo-km não informado)")
        photo_report = build_photo_report(
            anomalies,
            groups=groups,
            location_line=config.bridge_location_line,
        )

    report = report.model_copy(update={"groups": groups, "photo_report": photo_report})

    output_name = config.output_filename or default_output_filename(report)
    output_path = config.output_dir / output_name
    render_report(report, output_path, template_path=config.template_path)

    if assignments:
        photo_renames = rename_staged_photos_sequential(assignments, staged_dir)
    else:
        ordered_paths = [e.image_path for e in flatten_photo_entries(photo_report)]
        photo_renames = rename_staged_photos_from_paths(ordered_paths, staged_dir)

    elapsed = time.perf_counter() - start
    warnings = sum(1 for i in all_issues if i.severity == Severity.WARNING)
    errors = sum(1 for i in all_issues if i.severity == Severity.ERROR)

    logger.info(
        "Pipeline concluído em %.2fs | %d anomalia(s) | %d grupo(s) | %d foto(s) | saída: %s",
        elapsed,
        len(anomalies),
        len(groups),
        photo_report.total_photos,
        output_path,
    )

    return ReportResult(
        output_path=output_path,
        report=report,
        elapsed_seconds=elapsed,
        warnings=warnings,
        errors=errors,
        report_photos_dir=staged_dir,
        photo_renames=photo_renames,
    )
