"""Testes da ordem técnica do registro fotográfico."""

from backend.core.photo_numbering import assign_photo_codes, build_photo_prefix, iter_groups_document_order
from backend.core.text_generator import build_sections
from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup
from backend.rules.photo_section_order import (
    build_anomaly_photo_sort_key,
    photo_section_rank,
    resolve_photo_section,
    sort_anomalies_for_photo_report,
)


def _anomaly(
    local: str,
    number: str,
    *,
    face: str = "Leste",
    span: str | None = "Vão 1",
    row_index: int = 0,
) -> Anomaly:
    return Anomaly(
        local=local,
        number=number,
        face=face,
        span=span,
        anomaly_type="Fissura vertical",
        image_range_start="001",
        image_range_end="001",
        row_index=row_index,
        images=[f"/img/{local}{number}.jpg"],
    )


def test_resolve_photo_section_aliases() -> None:
    assert resolve_photo_section("L", "L") == "laje"
    assert resolve_photo_section("L1", "L") == "laje"
    assert resolve_photo_section("LB1", "LB") == "lajes_balanco"
    assert resolve_photo_section("VL2", "VL") == "vigas_longarinas"
    assert resolve_photo_section("AA1", "AA") == "aparelho_apoio"
    assert resolve_photo_section("ET1", "ET") == "infraestrutura"
    assert resolve_photo_section("JD3", "JD") == "juntas_dilatacao"
    assert resolve_photo_section("GC1", "GC") == "guarda_corpos"


def test_laje_first_in_photo_report() -> None:
    """Laje (L) deve preceder lajes em balanço e vigas longarinas."""
    anomalies = [
        _anomaly("VL", "1", row_index=1),
        _anomaly("LB", "1", row_index=2),
        _anomaly("L", "1", row_index=3),
        _anomaly("P", "1", row_index=4),
    ]
    ordered = sort_anomalies_for_photo_report(anomalies)
    assert [a.local for a in ordered] == ["L", "LB", "VL", "P"]


def test_engineering_order_excel_sequence_ignored() -> None:
    """Excel: VL, LB, JD, Pilar -> relatório: LB, VL, Pilar, JD."""
    anomalies = [
        _anomaly("VL", "2", row_index=1),
        _anomaly("LB", "1", row_index=2),
        _anomaly("JD", "1", row_index=3),
        _anomaly("P", "1", row_index=4),
    ]
    ordered = sort_anomalies_for_photo_report(anomalies)
    assert [a.local for a in ordered] == ["LB", "VL", "P", "JD"]


def test_element_number_within_section() -> None:
    anomalies = [
        _anomaly("VL", "5", row_index=1),
        _anomaly("VL", "1", row_index=2),
        _anomaly("VL", "2", row_index=3),
    ]
    ordered = sort_anomalies_for_photo_report(anomalies)
    assert [a.number for a in ordered] == ["1", "2", "5"]


def test_face_then_span_within_same_element() -> None:
    a = _anomaly("VL", "1", face="Oeste", span="Vão 5", row_index=1)
    b = _anomaly("VL", "1", face="Leste", span="Vão 1", row_index=2)
    c = _anomaly("VL", "1", face="Leste", span="Vão 2", row_index=3)
    ordered = sort_anomalies_for_photo_report([a, b, c])
    assert [x.row_index for x in ordered] == [2, 3, 1]


def test_assign_photo_codes_follows_engineering_order() -> None:
    groups = build_sections(
        [
            _anomaly("VL", "2", row_index=1),
            _anomaly("LB", "1", row_index=2),
            _anomaly("JD", "1", row_index=3),
            _anomaly("P", "1", row_index=4),
        ]
    )
    ordered_groups = iter_groups_document_order(groups)
    prefixes = [g.structural_prefix for g in ordered_groups]
    assert prefixes == ["LB", "VL", "P", "JD"]

    prefix = build_photo_prefix("E116", "244710")
    assignments, _ = assign_photo_codes(groups, prefix)
    assert assignments[0].anomaly.local == "LB"
    assert assignments[1].anomaly.local == "VL"
    assert assignments[2].anomaly.local == "P"
    assert assignments[3].anomaly.local == "JD"


def test_photo_section_rank_is_stable() -> None:
    assert photo_section_rank("laje") < photo_section_rank("lajes_balanco")
    assert photo_section_rank("laje") < photo_section_rank("vigas_longarinas")
    assert photo_section_rank("vigas_travamento") < photo_section_rank("infraestrutura")
    assert photo_section_rank("infraestrutura") < photo_section_rank("encontros")
    assert photo_section_rank("vigas_longarinas") < photo_section_rank("juntas_dilatacao")
    assert build_anomaly_photo_sort_key(_anomaly("LB", "1")) < build_anomaly_photo_sort_key(
        _anomaly("VL", "1")
    )
