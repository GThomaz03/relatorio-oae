"""Testes do gerador de texto."""

from backend.core.photo_generator import build_photo_report_from_assignments
from backend.core.photo_numbering import assign_photo_codes, build_photo_prefix
from backend.core.text_generator import (
    _canonical_description_override,
    build_sections,
    format_photo_references,
    generate_group_description,
    rebuild_group_descriptions,
)
from backend.models.anomaly import Anomaly
from backend.rules.grouping import clean_anomaly_type, normalize_anomaly_type, resolve_template_key


def test_canonical_override_prefers_original_in_duplicate_family() -> None:
    original = Anomaly(
        local="L",
        number="1",
        face="Inferior",
        span="BL01",
        anomaly_type="1.10 - Fissuras",
        image_range_start="1",
        image_range_end="1",
        client_id="anomaly-2",
        description_override="Abacaxi.",
    )
    duplicate = original.model_copy(
        update={
            "client_id": "anomaly-dup-1",
            "source_anomaly_client_id": "anomaly-2",
            "description_override": "Abacaxi 2.",
        },
        deep=True,
    )
    assert _canonical_description_override([duplicate, original]) == "Abacaxi"
    assert _canonical_description_override([duplicate, original]) != "Abacaxi 2"


def test_format_photo_references_uses_rsp_codes() -> None:
    single = format_photo_references(["E78K124F001S"])
    double = format_photo_references(["E78K124F001S", "E78K124F002S"])
    triple = format_photo_references(["E78K124F001S", "E78K124F002S", "E78K124F003S"])

    assert single == " (Foto E78K124F001S)"
    assert double == " (Fotos E78K124F001S e E78K124F002S)"
    assert triple == " (Fotos E78K124F001S, E78K124F002S e E78K124F003S)"


def test_normalize_anomaly_type() -> None:
    assert normalize_anomaly_type("Fissura Vertical") == "fissura_vertical"
    assert normalize_anomaly_type("1.10 - Fissuras verticais") == "fissuras_verticais"


def test_clean_anomaly_type() -> None:
    assert clean_anomaly_type("1.10 - Fissuras verticais com manchas umidade") == (
        "Fissuras verticais com manchas umidade"
    )


def test_resolve_template_key_fissura_vertical() -> None:
    assert resolve_template_key("1.10 - Fissuras verticais com manchas umidade") == "fissura_vertical"


def test_formatted_label_in_description() -> None:
    from backend.rules.anomaly_parser import parse_anomaly_text

    anomaly = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="4",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        semantics=parse_anomaly_text("1.10 - Fissuras verticais com manchas umidade"),
        crack_width="W0,15",
        image_range_start="187",
        image_range_end="187",
        images=["/tmp/IMG_0187.JPG"],
    )
    desc = generate_group_description([anomaly], include_photos=False)
    assert "manchas de umidade" in desc
    assert "0,15mm" in desc


def test_generate_description_lb_example() -> None:
    a = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="5",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="198",
        image_range_end="200",
        images=[
            "/tmp/IMG_0498.JPG",
            "/tmp/IMG_0499.JPG",
            "/tmp/IMG_0500.JPG",
        ],
    )
    desc = generate_group_description([a])
    assert desc.startswith("-\t")
    assert "1.10" not in desc
    assert "LB1" in desc
    assert "0,15mm" in desc
    assert "laje em balanço" in desc.lower()
    assert "vão 5" in desc
    assert "Fotos" in desc
    assert desc.endswith(";")


def test_generate_description_vl() -> None:
    a = Anomaly(
        local="VL1",
        number="1",
        face="Superior",
        anomaly_type="Fissura vertical",
        crack_width="0,10 mm",
        image_range_start="00136",
        image_range_end="00136",
        images=["/tmp/E116K24471000136S.jpg"],
    )
    desc = generate_group_description([a])
    assert desc.startswith("-\t")
    assert "VL1" in desc
    assert "Fotos" in desc or "Foto" in desc
    assert desc.endswith(";")


def test_one_line_per_anomaly_in_report() -> None:
    vao_4 = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="4",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="187",
        image_range_end="187",
        images=["/tmp/IMG_0187.JPG"],
        row_index=2,
    )
    vao_5 = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="5",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="198",
        image_range_end="198",
        images=["/tmp/IMG_0198.JPG"],
        row_index=3,
    )

    groups = build_sections([vao_5, vao_4])
    assert len(groups) == 2
    assert "vão 4" in groups[0].description
    assert "vão 5" in groups[1].description
    assert "vãos 4 e 5" not in groups[0].description
    assert "vãos 4 e 5" not in groups[1].description


def test_anomaly_order_by_element_number() -> None:
    lb1 = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="2",
        anomaly_type="1.10 - Fissuras verticais",
        crack_width="W0,15",
        image_range_start="162",
        image_range_end="162",
        images=["/tmp/a.jpg"],
        row_index=1,
    )
    lb2 = Anomaly(
        local="LB",
        number="2",
        face="Inferior",
        span="1",
        anomaly_type="1.10 - Fissuras verticais",
        crack_width="W0,15",
        image_range_start="170",
        image_range_end="170",
        images=["/tmp/b.jpg"],
        row_index=2,
    )

    groups = build_sections([lb2, lb1])
    assert groups[0].locals == ["LB1"]
    assert groups[1].locals == ["LB2"]


def test_photo_report_preserves_individual_spans_when_grouped() -> None:
    vao_4 = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="4",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="187",
        image_range_end="187",
        images=["/tmp/IMG_0187.JPG"],
    )
    vao_5 = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="5",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="198",
        image_range_end="198",
        images=["/tmp/IMG_0198.JPG"],
    )

    groups = build_sections([vao_4, vao_5])
    prefix = build_photo_prefix("E116", "244710")
    code_map = {
        "/tmp/IMG_0187.JPG": "E116K244710F032S",
        "/tmp/IMG_0198.JPG": "E116K244710F033S",
    }
    groups = rebuild_group_descriptions(groups, photo_code_map=code_map)
    assignments, _ = assign_photo_codes(groups, prefix)
    report = build_photo_report_from_assignments(assignments, photo_code_map=code_map)

    assert len(report.ordered_entries) == 2
    assert "vão 4" in report.ordered_entries[0].description_line.lower()
    assert "vão 5" in report.ordered_entries[1].description_line.lower()
    assert "vãos 4 e 5" not in report.ordered_entries[0].description_line.lower()
    assert "vãos 4 e 5" not in report.ordered_entries[1].description_line.lower()


def test_build_sections(sample_excel) -> None:
    from backend.core.parser_excel import parse_excel

    anomalies, _ = parse_excel(sample_excel)
    sections = build_sections(anomalies)
    assert all(s.description for s in sections)
