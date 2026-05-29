"""Testes de layout fotográfico e duplicação."""

from backend.core.photo_layout import PhotoLayoutEntry, materialize_anomalies_from_layout
from backend.core.photo_numbering import assign_photo_codes_from_anomalies, build_photo_prefix
from backend.core.text_generator import build_sections, rebuild_group_descriptions
from backend.models.anomaly import Anomaly


def _anomaly(row_index: int, token: str, span: str = "4") -> Anomaly:
    return Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span=span,
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start=token,
        image_range_end=token,
        nr_foto=token,
        row_index=row_index,
        images=[f"/tmp/IMG_{token}.JPG"],
    )


def test_duplicate_merge_photo_references_in_text() -> None:
    base = [_anomaly(2, "187"), _anomaly(3, "199", span="5")]
    layout = [
        PhotoLayoutEntry(
            anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="187",
            legend="Abacaxi",
        ),
        PhotoLayoutEntry(
            anomaly_id="anomaly-dup-1",
            source_anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="198",
            legend="Abacaxi 2",
        ),
        PhotoLayoutEntry(anomaly_id="anomaly-3", row_index=3, selected_photo="199"),
    ]
    ordered = materialize_anomalies_from_layout(base, layout)
    assert len(ordered) == 3
    assert ordered[1].nr_foto == "198"
    assert ordered[0].source_anomaly_client_id is None
    assert ordered[1].source_anomaly_client_id == "anomaly-2"
    assert "Abacaxi" in (ordered[0].description_override or "")
    assert "Abacaxi 2" in (ordered[1].description_override or "")
    assert ordered[0].description_override != ordered[1].description_override

    groups = build_sections(ordered)
    assert len(groups) == 2
    merged = next(g for g in groups if len(g.members) == 2)
    assert len(merged.members) == 2

    prefix = build_photo_prefix("E116", "244710")
    ordered[0].images = ["/tmp/IMG_187.JPG"]
    ordered[1].images = ["/tmp/IMG_198.JPG"]
    ordered[2].images = ["/tmp/IMG_199.JPG"]
    code_map = {
        "/tmp/IMG_187.JPG": "E116K244710F001S",
        "/tmp/IMG_198.JPG": "E116K244710F002S",
        "/tmp/IMG_199.JPG": "E116K244710F003S",
    }
    groups = rebuild_group_descriptions(groups, photo_code_map=code_map)
    merged = next(g for g in groups if len(g.members) == 2)
    assert "Abacaxi" in merged.description
    assert "Fissuras" not in merged.description
    assert "(Fotos E116K244710F001S e E116K244710F002S)" in merged.description

    assignments, _ = assign_photo_codes_from_anomalies(ordered, groups, prefix)
    assert len(assignments) == 3
    assert assignments[0].anomaly.nr_foto == "187"
    assert assignments[1].anomaly.nr_foto == "198"


def test_duplicate_photo_report_keeps_per_photo_legends() -> None:
    from backend.core.photo_generator import (
        _description_line,
        build_photo_report_from_assignments,
    )
    base = [_anomaly(2, "187")]
    layout = [
        PhotoLayoutEntry(
            anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="187",
            legend="Abacaxi",
        ),
        PhotoLayoutEntry(
            anomaly_id="anomaly-dup-1",
            source_anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="198",
            legend="Abacaxi 2",
        ),
    ]
    ordered = materialize_anomalies_from_layout(base, layout)
    ordered[0].images = ["/tmp/IMG_187.JPG"]
    ordered[1].images = ["/tmp/IMG_198.JPG"]

    groups = build_sections(ordered)
    prefix = build_photo_prefix("E116", "244710")
    assignments, code_map = assign_photo_codes_from_anomalies(ordered, groups, prefix)
    report = build_photo_report_from_assignments(
        assignments,
        location_line="Ponte — BR — Km —",
        photo_code_map=code_map,
    )

    assert len(report.ordered_entries) == 2
    assert "Abacaxi" in report.ordered_entries[0].description_line
    assert "Abacaxi 2" in report.ordered_entries[1].description_line
    assert _description_line(ordered[0]).rstrip(".") == report.ordered_entries[0].description_line.rstrip(
        "."
    )
    assert _description_line(ordered[1]).rstrip(".") == report.ordered_entries[1].description_line.rstrip(
        "."
    )


def test_layout_override_drives_anomaly_report_bullet() -> None:
    from backend.core.text_generator import generate_group_description

    base = [_anomaly(2, "187")]
    custom = "Legenda unificada entre relatório fotográfico e de anomalias"
    layout = [
        PhotoLayoutEntry(
            anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="187",
            legend=custom,
        ),
    ]
    ordered = materialize_anomalies_from_layout(base, layout)
    desc = generate_group_description(ordered, include_photos=False)
    assert custom in desc
    assert "1.10" not in desc


def test_layout_applies_custom_legend() -> None:
    base = [_anomaly(2, "187")]
    custom = "Legenda editada pelo utilizador"
    layout = [
        PhotoLayoutEntry(
            anomaly_id="anomaly-2",
            row_index=2,
            selected_photo="187",
            legend=custom,
        ),
    ]
    ordered = materialize_anomalies_from_layout(base, layout)
    assert len(ordered) == 1
    assert ordered[0].view == f"{custom}."


def test_layout_partial_failure_raises() -> None:
    base = [_anomaly(2, "187")]
    layout = [
        PhotoLayoutEntry(anomaly_id="anomaly-2", row_index=2, selected_photo="187"),
        PhotoLayoutEntry(anomaly_id="missing-99", row_index=999, selected_photo="1"),
    ]
    from backend.core.photo_layout import LayoutMaterializationError

    try:
        materialize_anomalies_from_layout(base, layout)
        raise AssertionError("expected LayoutMaterializationError")
    except LayoutMaterializationError as exc:
        assert exc.applied == 1
        assert exc.expected == 2
        assert "missing-99" in exc.skipped_ids
