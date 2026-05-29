"""Testes do parser semântico de anomalias."""

from backend.models.anomaly import Anomaly
from backend.rules.anomaly_parser import (
    formatted_anomaly_label,
    normalize_for_match,
    parse_anomaly_text,
    resolve_template_key,
)
from backend.core.text_generator import generate_group_description


def test_parse_fissuras_verticais_com_manchas_umidade() -> None:
    parsed = parse_anomaly_text("1.10 - Fissuras verticais com manchas umidade")

    assert parsed.base_key == "fissuras_verticais"
    assert parsed.base_label == "Fissuras verticais"
    assert parsed.modifier_keys == ["manchas_umidade"]
    assert parsed.modifier_labels == ["manchas de umidade"]
    assert parsed.formatted_label == "Fissuras verticais com manchas de umidade"
    assert parsed.template_key == "fissura_vertical"
    assert parsed.grouping_key == "fissuras_verticais+manchas_umidade"
    assert parsed.original_text.startswith("1.10")


def test_parse_fissuras_horizontais_c_umidade() -> None:
    parsed = parse_anomaly_text("Fissuras horizontais c/ umidade")

    assert parsed.base_key == "fissuras_horizontais"
    assert "manchas_umidade" in parsed.modifier_keys
    assert parsed.formatted_label == "Fissuras horizontais com manchas de umidade"


def test_parse_trincas_com_eflorescencia() -> None:
    parsed = parse_anomaly_text("Trincas com eflorescência")

    assert parsed.base_key == "trincas"
    assert parsed.modifier_keys == ["eflorescencia"]
    assert parsed.formatted_label == "Trincas com eflorescência"


def test_normalize_connectors_and_accents() -> None:
    assert normalize_for_match("Fissuras  horizontais  c/ umidade") == (
        "fissuras horizontais com umidade"
    )


def test_resolve_template_key_uses_base_not_modifier() -> None:
    assert resolve_template_key("Fissuras verticais com manchas umidade") == "fissura_vertical"


def test_report_description_uses_formatted_label() -> None:
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
    assert "manchas umidade" not in desc.replace("manchas de umidade", "")


def test_formatted_anomaly_label_helper() -> None:
    assert formatted_anomaly_label("Fissuras verticais com manchas umidade") == (
        "Fissuras verticais com manchas de umidade"
    )
