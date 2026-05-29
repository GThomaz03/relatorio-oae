"""Testes do gerador fotográfico."""

from backend.core.parser_excel import parse_excel
from backend.core.parser_images import attach_images_to_anomalies
from backend.core.photo_generator import build_photo_report, build_photo_report_from_assignments
from backend.core.photo_numbering import assign_photo_codes, build_photo_prefix
from backend.core.text_generator import build_sections, description_body_for_anomaly
from backend.models.anomaly import Anomaly


def test_build_photo_report(sample_excel, sample_images) -> None:
    anomalies, _ = parse_excel(sample_excel)
    anomalies, _ = attach_images_to_anomalies(anomalies, sample_images)
    groups = build_sections(anomalies)
    report = build_photo_report(
        anomalies,
        groups=groups,
        location_line="Ponte teste — BR116 — Km 244+710",
    )
    assert report.total_photos == 3
    first = report.sections[0].entries[0]
    assert first.code
    assert first.location_line.startswith("Ponte teste")
    assert first.description_line.endswith(".")


def test_photo_caption_uses_individual_anomaly_description(sample_excel, sample_images) -> None:
    anomalies, _ = parse_excel(sample_excel)
    anomalies, _ = attach_images_to_anomalies(anomalies, sample_images)
    groups = build_sections(anomalies)
    report = build_photo_report(anomalies, groups=groups)

    def expected_line(anomaly: Anomaly) -> str:
        if anomaly.view and str(anomaly.view).strip():
            return str(anomaly.view).strip()
        return description_body_for_anomaly(anomaly)

    for entry in report.ordered_entries:
        anomaly = next(
            a
            for a in anomalies
            if entry.anomaly_local == a.local or entry.anomaly_local.startswith(a.local)
        )
        assert entry.description_line.rstrip(".") == expected_line(anomaly)
