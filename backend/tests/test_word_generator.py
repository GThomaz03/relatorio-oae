"""Testes do gerador Word."""

from pathlib import Path

from backend.core.parser_excel import parse_excel
from backend.core.parser_images import attach_images_to_anomalies
from backend.core.photo_generator import build_photo_report
from backend.core.text_generator import build_sections
from backend.core.word_generator import render_report
from backend.models.inspection import InspectionReport, ReportMetadata


def test_render_report(sample_excel, sample_images, sample_template, output_dir) -> None:
    anomalies, _ = parse_excel(sample_excel)
    anomalies, _ = attach_images_to_anomalies(anomalies, sample_images)
    groups = build_sections(anomalies)
    photo_report = build_photo_report(anomalies, groups=groups)

    report = InspectionReport(
        metadata=ReportMetadata(
            excel_path=sample_excel,
            images_dir=sample_images,
            template_path=sample_template,
            bridge_id="E116",
        ),
        anomalies=anomalies,
        groups=groups,
        photo_report=photo_report,
    )

    out = output_dir / "test_report.docx"
    result = render_report(report, out, template_path=sample_template)
    assert result.exists()
    assert result.stat().st_size > 3000
