"""Serialização do relatório para JSON consumido pelo frontend."""

from __future__ import annotations

from pathlib import Path

from backend.config import DEFAULT_TEMPLATE
from backend.core.photo_generator import build_photo_report, build_photo_report_from_assignments, flatten_photo_entries
from backend.core.parser_images import (
    build_image_index,
    expand_image_range,
    resolve_image_for_token,
)
from backend.core.photo_numbering import assign_photo_codes, build_photo_prefix
from backend.core.text_generator import description_body_for_anomaly
from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup, InspectionReport, PhotoEntry
from backend.models.structure import parse_local_code, structural_label_pt
from backend.core.validators import Severity, ValidationIssue


def _element_label(anomaly: Anomaly) -> str:
    code = parse_local_code(anomaly.local)
    if code:
        label = structural_label_pt(code)
        if anomaly.number:
            return f"{label} {anomaly.number}".strip()
        return label
    return anomaly.local


def _anomaly_status(anomaly: Anomaly, issues: list[ValidationIssue]) -> str:
    row_issues = [i for i in issues if i.row_index == anomaly.row_index]
    if any(i.severity == Severity.ERROR for i in row_issues):
        return "error"
    if not anomaly.images:
        return "error"
    if any(i.severity == Severity.WARNING for i in row_issues):
        return "warning"
    return "ok"


def _legend_for_anomaly(anomaly: Anomaly) -> str:
    if anomaly.view and str(anomaly.view).strip():
        text = str(anomaly.view).strip()
        return text if text.endswith(".") else f"{text}."
    body = description_body_for_anomaly(anomaly)
    return body if body.endswith(".") else f"{body}."


def build_analysis_payload(
    report: InspectionReport,
    groups: list[AnomalyGroup],
    photo_entries: list[PhotoEntry],
    photo_code_map: dict[str, str],
    issues: list[ValidationIssue],
    project_id: str,
    api_base: str = "/api",
) -> dict:
    source_dir = report.metadata.source_images_dir
    image_index = build_image_index(source_dir) if source_dir else None

    def build_available_images(anomaly: Anomaly) -> list[dict]:
        if not image_index:
            return []
        try:
            tokens = expand_image_range(anomaly.image_range_start, anomaly.image_range_end)
        except Exception:
            return []
        options: list[dict] = []
        for token in tokens:
            paths, _ = resolve_image_for_token(image_index, token)
            if not paths:
                continue
            img_name = Path(paths[0]).name
            options.append(
                {
                    "photoNumber": str(int(token)) if token.isdigit() else token,
                    "imagePath": img_name,
                    "thumbnailUrl": f"{api_base}/projects/{project_id}/images/{img_name}?thumb=1&size=320",
                }
            )
        return options

    anomalies_json: list[dict] = []
    anomaly_key_to_id: dict[tuple[str, str], str] = {}
    anomaly_row_to_id: dict[int, str] = {}
    anomaly_image_to_id: dict[str, str] = {}
    for idx, anomaly in enumerate(report.anomalies):
        available_images = build_available_images(anomaly)
        selected_name = Path(anomaly.images[0]).name if anomaly.images else None
        selected = next((opt for opt in available_images if opt["imagePath"] == selected_name), None)
        if not selected and available_images:
            selected = available_images[0]

        image_path = selected["imagePath"] if selected else selected_name
        thumb = selected["thumbnailUrl"] if selected else None
        if image_path and not thumb:
            thumb = f"{api_base}/projects/{project_id}/images/{Path(image_path).name}?thumb=1&size=320"

        selected_number = selected["photoNumber"] if selected else (
            str(int(anomaly.resolved_photo_token))
            if anomaly.resolved_photo_token.isdigit()
            else anomaly.resolved_photo_token
        )

        anomaly_id = (
            f"anomaly-{anomaly.row_index}"
            if anomaly.row_index is not None
            else f"anomaly-{idx + 1}"
        )
        anomalies_json.append(
            {
                "id": anomaly_id,
                "rowIndex": anomaly.row_index,
                "photoToken": anomaly.resolved_photo_token,
                "imagePath": image_path,
                "thumbnailUrl": thumb,
                "element": _element_label(anomaly),
                "anomalyType": anomaly.anomaly_type,
                "description": anomaly.observations or anomaly.anomaly_type,
                "legend": _legend_for_anomaly(anomaly),
                "observations": anomaly.observations or "",
                "face": anomaly.face or "",
                "local": anomaly.local,
                "status": _anomaly_status(anomaly, issues),
                "sequenceIndex": idx + 1,
                "rangeStart": anomaly.image_range_start,
                "rangeEnd": anomaly.image_range_end,
                "rangeLabel": f"Fotos {anomaly.image_range_start} a {anomaly.image_range_end}",
                "selectedPhotoNumber": selected_number,
                "availableImages": available_images,
            }
        )
        anomaly_key_to_id[(anomaly.local, anomaly.number or "")] = anomaly_id
        if anomaly.row_index is not None:
            anomaly_row_to_id[anomaly.row_index] = anomaly_id
        if image_path:
            anomaly_image_to_id[Path(image_path).name] = anomaly_id

    photos_json: list[dict] = []
    for entry in photo_entries:
        name = Path(entry.image_path).name
        anomaly_id = None
        if entry.anomaly_row_index is not None:
            anomaly_id = anomaly_row_to_id.get(entry.anomaly_row_index)
        if not anomaly_id:
            anomaly_id = anomaly_key_to_id.get((entry.anomaly_local, entry.anomaly_number or ""))
        if not anomaly_id:
            anomaly_id = anomaly_image_to_id.get(name)
        photos_json.append(
            {
                "id": f"photo-{entry.sequence_index}",
                "anomalyId": anomaly_id,
                "anomalyRowIndex": entry.anomaly_row_index,
                "code": entry.code,
                "imagePath": name,
                "thumbnailUrl": f"{api_base}/projects/{project_id}/images/{name}?thumb=1&size=320",
                "legend": entry.description_line,
                "locationLine": entry.location_line,
                "sequenceIndex": entry.sequence_index,
            }
        )

    images_found = sum(1 for a in report.anomalies if a.images)
    images_missing = len(report.anomalies) - images_found
    inconsistencies = sum(1 for a in anomalies_json if a["status"] == "warning")
    elements = sorted({a["element"] for a in anomalies_json if a["element"]})

    from datetime import datetime, timezone

    return {
        "summary": {
            "anomalyCount": len(report.anomalies),
            "imagesFound": images_found,
            "imagesMissing": images_missing,
            "inconsistencies": inconsistencies,
            "structuralElements": elements,
        },
        "anomalies": anomalies_json,
        "photos": photos_json,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "warnings": [i.model_dump() for i in issues if i.severity == Severity.WARNING],
        "errors": [i.model_dump() for i in issues if i.severity == Severity.ERROR],
    }


def run_analysis_pipeline(
    excel: Path,
    images: Path,
    staging_dir: Path,
    bridge_id: str | None,
    photo_km: str | None,
    photo_direction: str,
    bridge_location_line: str,
) -> tuple[InspectionReport, list[AnomalyGroup], list[PhotoEntry], dict[str, str], list[ValidationIssue]]:
    from backend.core.parser_excel import parse_excel
    from backend.core.report_image_staging import stage_report_images
    from backend.core.text_generator import build_sections, rebuild_group_descriptions
    from backend.core.validators import validate_inspection
    from backend.models.inspection import ReportMetadata

    from backend.rules.photo_section_order import sort_anomalies_for_photo_report

    anomalies, parse_issues = parse_excel(excel)
    anomalies, staging_issues = stage_report_images(anomalies, images, staging_dir)
    anomalies = sort_anomalies_for_photo_report(anomalies)

    metadata = ReportMetadata(
        excel_path=excel.resolve(),
        images_dir=staging_dir.resolve(),
        template_path=DEFAULT_TEMPLATE,
        bridge_id=bridge_id,
        bridge_location_line=bridge_location_line,
        photo_km=photo_km,
        photo_direction=photo_direction,
        source_images_dir=images.resolve(),
        report_photos_dir=staging_dir.resolve(),
    )
    report = InspectionReport(metadata=metadata, anomalies=anomalies)
    validation_issues = validate_inspection(report, strict=False)
    all_issues = parse_issues + staging_issues + validation_issues

    groups = build_sections(anomalies)
    photo_code_map: dict[str, str] = {}

    if bridge_id and photo_km:
        prefix = build_photo_prefix(bridge_id, photo_km)
        assignments, photo_code_map = assign_photo_codes(
            groups, prefix, direction=photo_direction
        )
        groups = rebuild_group_descriptions(groups, photo_code_map=photo_code_map)
        photo_report = build_photo_report_from_assignments(
            assignments,
            location_line=bridge_location_line,
            photo_code_map=photo_code_map,
        )
    else:
        photo_report = build_photo_report(
            anomalies,
            groups=groups,
            location_line=bridge_location_line,
        )

    report = report.model_copy(update={"groups": groups, "photo_report": photo_report})
    entries = flatten_photo_entries(photo_report)
    return report, groups, entries, photo_code_map, all_issues
