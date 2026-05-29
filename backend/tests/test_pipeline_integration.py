"""Teste de integração do pipeline completo."""

from backend.services.report_pipeline import ReportConfig, generate_report


def test_generate_report_e2e(sample_excel, sample_images, sample_template, output_dir) -> None:
    config = ReportConfig(
        excel_path=sample_excel,
        images_dir=sample_images,
        template_path=sample_template,
        output_dir=output_dir,
        bridge_id="E116",
        photo_km="244710",
        strict=False,
    )
    result = generate_report(config)
    assert result.output_path.exists()
    assert len(result.report.anomalies) == 3
    assert len(result.report.groups) >= 2
    assert result.report.photo_report is not None
    assert result.report.photo_report.total_photos == 3
    assert result.elapsed_seconds < 120

    assert result.report_photos_dir is not None
    assert result.report_photos_dir.is_dir()
    renamed = list(result.report_photos_dir.glob("*-*.jpg"))
    assert len(renamed) == 3
    assert any(p.name.startswith("1-") for p in renamed)

    first_entry = result.report.photo_report.ordered_entries[0]
    assert first_entry.code.startswith("E116K244710F")
    assert first_entry.code.endswith("S")
    assert any(
        "(Foto E116K244710F" in g.description or "(Fotos E116K244710F" in g.description
        for g in result.report.groups
        if g.description
    )
