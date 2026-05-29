"""Testes de parsing estrutural e classificação de locais."""

from pathlib import Path

import pandas as pd

from backend.core.document_structure import build_anomaly_macros
from backend.core.parser_excel import parse_excel
from backend.core.text_generator import build_sections, generate_group_description
from backend.models.anomaly import Anomaly
from backend.models.structure import (
    element_heading_for_code,
    format_local_with_number,
    hierarchy_for_code,
    parse_local_code,
)


def test_parse_local_code_pista_not_pilar() -> None:
    assert parse_local_code("PISTA") == "PISTA"
    assert parse_local_code("PISTA") != "P"


def test_parse_local_code_pilar_with_number() -> None:
    assert parse_local_code("P8") == "P"
    assert parse_local_code("P12") == "P"
    assert parse_local_code("PF") == "PF"


def test_format_local_without_number() -> None:
    assert format_local_with_number("PISTA", None) == "PISTA"
    assert format_local_with_number("BUZ", None) == "BUZ"
    assert format_local_with_number("JD", "1") == "JD1"


def test_hierarchy_pista_is_pavimento() -> None:
    macro, element = hierarchy_for_code("PISTA")
    assert macro == "PAVIMENTO"
    assert element == "Pavimento flexível"


def test_element_heading_pilares() -> None:
    assert element_heading_for_code("P") == "Pilares"


def test_pista_descriptions_match_expected_pattern() -> None:
    acumulo = Anomaly(
        local="PISTA",
        number=None,
        face="Sobre a Obra",
        anomaly_type="4.4 - Acúmulo de detritos, ocorrência de agentes agressivos",
        image_range_start="406",
        image_range_end="407",
        images=["/tmp/IMG_0406.JPG", "/tmp/IMG_0407.JPG"],
    )
    taxa = Anomaly(
        local="PISTA",
        number=None,
        face="Sobre a Obra",
        anomaly_type="Ausência de taxa refletiva",
        image_range_start="408",
        image_range_end="409",
        images=["/tmp/IMG_0408.JPG", "/tmp/IMG_0409.JPG"],
    )

    desc_acumulo = generate_group_description([acumulo])
    desc_taxa = generate_group_description([taxa])

    assert "pilar" not in desc_acumulo.lower()
    assert "PISTA" not in desc_acumulo
    assert "bordo do pavimento flexível" in desc_acumulo
    assert "Sobre a Obra" not in desc_acumulo

    assert "pilar" not in desc_taxa.lower()
    assert "PISTA" not in desc_taxa
    assert "taxa reflexiva no pavimento flexível" in desc_taxa


def test_jd_grouping_separates_by_number() -> None:
    a1 = Anomaly(
        local="JD",
        number="1",
        face="Sobre a Obra",
        anomaly_type="3.11 - Acúmulo de detritos no junta de dilatação",
        image_range_start="398",
        image_range_end="398",
        images=["/tmp/IMG_0398.JPG"],
    )
    a2 = Anomaly(
        local="JD",
        number="2",
        face="Sobre a Obra",
        anomaly_type="3.11 - Acúmulo de detritos no junta de dilatação",
        image_range_start="410",
        image_range_end="410",
        images=["/tmp/IMG_0410.JPG"],
    )

    groups = build_sections([a1, a2])
    assert len(groups) == 2
    assert "JD1" in groups[0].description
    assert "JD2" in groups[1].description
    assert "JD1 e JD2" not in groups[0].description


def test_pilar_preposition_no() -> None:
    anomaly = Anomaly(
        local="P",
        number="8",
        face="Norte",
        anomaly_type="1.16 - Desplacamento",
        image_range_start="473",
        image_range_end="473",
        images=["/tmp/IMG_0473.JPG"],
    )
    desc = generate_group_description([anomaly])
    assert "no pilar P8" in desc
    assert "na pilar" not in desc


def test_parser_pista_empty_number(tmp_path: Path) -> None:
    path = tmp_path / "pista.xlsx"
    df = pd.DataFrame(
        [
            {
                "Local": "PISTA",
                "Núm.": None,
                "Face": "Sobre a Obra",
                "Anomalia": "Ausência de taxa refletiva",
                "Quant Fotos": 1,
                "Disp.": "Sim",
                "Cam inicial": 408,
                "Cam final": 408,
            }
        ]
    )
    df.to_excel(path, index=False, sheet_name="db_ficha")
    anomalies, _ = parse_excel(path)
    assert len(anomalies) == 1
    assert anomalies[0].number is None
    desc = generate_group_description([anomalies[0]])
    assert "pavimento flexível" in desc
    assert "PISTA6" not in desc
    assert "PISTA" not in desc


def test_pavimento_macro_without_subheading() -> None:
    anomaly = Anomaly(
        local="PISTA",
        number=None,
        face="Sobre a Obra",
        anomaly_type="Ausência de taxa refletiva",
        image_range_start="408",
        image_range_end="408",
        images=["/tmp/IMG_0408.JPG"],
    )
    groups = build_sections([anomaly])
    macros = build_anomaly_macros(groups)
    pavimento = next(m for m in macros if m["title"] == "PAVIMENTO")
    assert len(pavimento["elements"]) == 1
    assert pavimento["elements"][0]["title"] == ""
