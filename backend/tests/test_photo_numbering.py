"""Testes de numeração fotográfica RSP."""

from backend.core.photo_generator import build_photo_report_from_assignments, flatten_photo_entries
from backend.core.photo_numbering import (
    assign_photo_codes,
    build_photo_prefix,
    build_rsp_photo_code,
)
from backend.core.text_generator import rebuild_group_descriptions
from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup, PhotoEntry, PhotoReport


def _group(
    group_id: str,
    local: str,
    number: str,
    anomaly_type: str,
    images: list[str],
    prefix: str = "VL",
) -> AnomalyGroup:
    anomaly = Anomaly(
        local=local,
        number=number,
        face="Superior",
        anomaly_type=anomaly_type,
        image_range_start="001",
        image_range_end="001",
        images=images,
    )
    return AnomalyGroup(
        group_id=group_id,
        section_id=prefix,
        anomaly_type=anomaly_type,
        face="Superior",
        view=None,
        structural_prefix=prefix,
        members=[anomaly],
        locals=[f"{local}{number}" if number else local],
        description="",
    )


def test_build_rsp_photo_code() -> None:
    assert build_rsp_photo_code("E116K244710", 1) == "E116K244710F001S"
    assert build_rsp_photo_code("E116K244710", 30) == "E116K244710F030S"


def test_build_photo_prefix() -> None:
    assert build_photo_prefix("E116", "244710") == "E116K244710"
    assert build_photo_prefix("E116", "244+710") == "E116K244710"


def test_assign_photo_codes_sequential() -> None:
    groups = [
        _group("G001", "VL", "1", "Fissura vertical", ["/img/a.jpg"], prefix="VL"),
        _group("G002", "VL", "2", "Fissura vertical", ["/img/b.jpg"], prefix="VL"),
        _group("G003", "P", "8", "Desplacamento", ["/img/c.jpg"], prefix="P"),
    ]
    prefix = build_photo_prefix("E116", "244710")
    assignments, code_map = assign_photo_codes(groups, prefix)

    assert len(assignments) == 3
    assert assignments[0].report_code == "E116K244710F001S"
    assert assignments[1].report_code == "E116K244710F002S"
    assert assignments[2].report_code == "E116K244710F003S"
    assert code_map["/img/a.jpg"] == "E116K244710F001S"


def test_assign_photo_codes_deduplicates_same_image() -> None:
    groups = [
        _group("G001", "VL", "1", "Fissura", ["/img/shared.jpg"], prefix="VL"),
        _group("G002", "VL", "2", "Fissura", ["/img/shared.jpg"], prefix="VL"),
    ]
    prefix = build_photo_prefix("E116", "244710")
    assignments, code_map = assign_photo_codes(groups, prefix)

    assert len(assignments) == 1
    assert code_map["/img/shared.jpg"] == "E116K244710F001S"


def test_rebuild_group_descriptions_uses_rsp_codes() -> None:
    anomaly = Anomaly(
        local="VL1",
        number="1",
        face="Superior",
        anomaly_type="Fissura vertical",
        image_range_start="001",
        image_range_end="001",
        images=["/img/a.jpg"],
    )
    group = AnomalyGroup(
        group_id="G001",
        section_id="VL",
        anomaly_type="Fissura vertical",
        face="Superior",
        view=None,
        structural_prefix="VL",
        members=[anomaly],
        locals=["VL1"],
        description="-build",
    )
    code_map = {"/img/a.jpg": "E116K244710F001S"}
    updated = rebuild_group_descriptions([group], photo_code_map=code_map)
    assert "(Foto E116K244710F001S)" in updated[0].description
    assert "IMG_" not in updated[0].description


def test_photo_caption_matches_group_bullet() -> None:
    from backend.core.text_generator import description_from_group_bullet, generate_group_description

    anomaly = Anomaly(
        local="LB",
        number="1",
        face="Inferior",
        span="2",
        anomaly_type="1.10 - Fissuras verticais com manchas umidade",
        crack_width="W0,15",
        image_range_start="001",
        image_range_end="001",
        images=["/img/a.jpg"],
    )
    code_map = {"/img/a.jpg": "E116K244710F031S"}
    description = generate_group_description([anomaly], photo_code_map=code_map)
    group = AnomalyGroup(
        group_id="G001",
        section_id="LB",
        anomaly_type="Fissuras verticais",
        face="Inferior",
        view=None,
        structural_prefix="LB",
        members=[anomaly],
        locals=["LB1"],
        description=description,
    )
    prefix = build_photo_prefix("E116", "244710")
    assignments, _ = assign_photo_codes([group], prefix)
    report = build_photo_report_from_assignments(assignments, photo_code_map=code_map)
    entry = flatten_photo_entries(report)[0]

    expected_body = description_from_group_bullet(description)
    assert entry.description_line.rstrip(".") == expected_body
    assert "vão 2" in entry.description_line.lower()


def test_photo_report_from_assignments_preserves_order() -> None:
    groups = [
        _group(
            "G001",
            "VL",
            "1",
            "Fissura",
            ["/img/z.jpg", "/img/a.jpg"],
            prefix="VL",
        ),
    ]
    prefix = build_photo_prefix("E116", "244710")
    assignments, code_map = assign_photo_codes(groups, prefix)
    report = build_photo_report_from_assignments(assignments, photo_code_map=code_map)

    flat = flatten_photo_entries(report)
    assert flat[0].code == "E116K244710F001S"
    assert flat[1].code == "E116K244710F002S"


def test_flatten_photo_entries_preserves_ordered_entries() -> None:
    report = PhotoReport(
        ordered_entries=[
            PhotoEntry(
                image_path="/z.jpg",
                code="E116K244710F002S",
                location_line="",
                description_line="x.",
                caption="",
                anomaly_local="VL1",
                sequence_index=1,
                figure_number=1,
            ),
            PhotoEntry(
                image_path="/a.jpg",
                code="E116K244710F001S",
                location_line="",
                description_line="y.",
                caption="",
                anomaly_local="VL1",
                sequence_index=2,
                figure_number=2,
            ),
        ],
        total_photos=2,
    )
    flat = flatten_photo_entries(report)
    assert flat[0].code == "E116K244710F002S"
    assert flat[1].code == "E116K244710F001S"
