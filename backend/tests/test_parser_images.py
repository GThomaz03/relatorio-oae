"""Testes do parser de imagens."""

from pathlib import Path

from PIL import Image as PILImage

from backend.core.parser_excel import parse_excel
from backend.core.parser_images import (
    attach_images_to_anomalies,
    build_image_index,
    count_image_files,
    expand_image_range,
    parse_range_cell,
    resolve_images_for_range,
)
from backend.core.validators import Severity


def test_parse_range_cell() -> None:
    start, end = parse_range_cell("00136 até 00138")
    assert start == "00136"
    assert end == "00138"


def test_build_image_index(sample_images: Path) -> None:
    index = build_image_index(sample_images)
    assert len(index.all_files()) == 5


def test_resolve_images_for_range(sample_images: Path) -> None:
    index = build_image_index(sample_images)
    paths, issues = resolve_images_for_range(index, "00136", "00138")
    assert len(paths) == 3
    assert not any(i.severity == Severity.ERROR for i in issues)


def test_attach_images(sample_excel: Path, sample_images: Path) -> None:
    anomalies, _ = parse_excel(sample_excel)
    updated, issues = attach_images_to_anomalies(anomalies, sample_images)
    assert len(updated[0].images) == 1
    assert len(updated[1].images) == 1
    assert len(updated[2].images) == 1
    assert all(Path(p).exists() for p in updated[0].images)


def test_build_image_index_nested_folder(tmp_path: Path) -> None:
    """Layout real do upload: images/MinhaObra/E116K....jpg"""
    obra = tmp_path / "MinhaObra"
    obra.mkdir()
    for token in ("00136", "00137", "00138"):
        img = PILImage.new("RGB", (80, 60), color=(120, 120, 120))
        img.save(obra / f"E116K244710{token}S.jpg")

    assert count_image_files(tmp_path) == 3
    index = build_image_index(tmp_path)
    assert len(index.all_files()) == 3

    paths, issues = resolve_images_for_range(index, "00136", "00138")
    assert len(paths) == 3
    assert not any(i.severity == Severity.ERROR for i in issues)


def test_attach_images_nested_folder(sample_excel: Path, tmp_path: Path) -> None:
    obra = tmp_path / "PastaObra"
    obra.mkdir()
    for token in ("00136", "00139", "00140"):
        img = PILImage.new("RGB", (80, 60), color=(100, 100, 100))
        img.save(obra / f"E116K244710{token}S.jpg")

    anomalies, _ = parse_excel(sample_excel)
    updated, _ = attach_images_to_anomalies(anomalies, tmp_path)
    assert len(updated[0].images) == 1
    assert len(updated[1].images) == 1
    assert len(updated[2].images) == 1
    assert all(Path(p).exists() for p in updated[0].images)
