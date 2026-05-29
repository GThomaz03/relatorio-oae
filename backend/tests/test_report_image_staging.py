"""Testes de staging e nr_foto."""

from pathlib import Path

import pandas as pd
from PIL import Image as PILImage

from backend.core.parser_excel import parse_excel
from backend.core.parser_images import build_image_index, resolve_image_for_token
from backend.core.report_image_staging import (
    ordered_report_filename,
    rename_staged_photos_from_paths,
    sequential_report_filename,
    stage_report_images,
)
from backend.models.anomaly import Anomaly


def test_resolved_photo_token_priority() -> None:
    a = Anomaly(
        local="JD",
        number="1",
        face="Superior",
        anomaly_type="Teste",
        nr_foto="98",
        image_range_start="98",
        image_range_end="99",
    )
    assert a.resolved_photo_token == "98"

    b = a.model_copy(update={"nr_foto": None})
    assert b.resolved_photo_token == "98"


def test_resolve_img_by_token(tmp_path: Path) -> None:
    img_dir = tmp_path / "src"
    img_dir.mkdir()
    img = PILImage.new("RGB", (10, 10), color=(1, 2, 3))
    img.save(img_dir / "IMG_0098.JPG")

    index = build_image_index(img_dir)
    paths, _ = resolve_image_for_token(index, "98")
    assert len(paths) == 1
    assert Path(paths[0]).name.upper() == "IMG_0098.JPG"


def test_stage_report_images_deduplicates(tmp_path: Path) -> None:
    src = tmp_path / "originais"
    src.mkdir()
    dest = tmp_path / "fotos_relatorio"
    img = PILImage.new("RGB", (10, 10), color=(1, 2, 3))
    img.save(src / "E116K24471000136S.jpg")

    anomalies = [
        Anomaly(
            local="VL1",
            number="1",
            face="Sup",
            anomaly_type="Fissura",
            image_range_start="00136",
            image_range_end="00138",
            nr_foto="00136",
        ),
        Anomaly(
            local="VL2",
            number="2",
            face="Sup",
            anomaly_type="Fissura",
            image_range_start="00136",
            image_range_end="00136",
            nr_foto="00136",
        ),
    ]

    updated, _ = stage_report_images(anomalies, src, dest)
    assert len(list(dest.iterdir())) == 1
    assert all(a.images[0].startswith(str(dest)) for a in updated if a.images)


def test_rename_sequential_four_digits(tmp_path: Path) -> None:
    staged = tmp_path / "fotos_relatorio"
    staged.mkdir()
    img = PILImage.new("RGB", (10, 10), color=(1, 2, 3))
    p1 = staged / "IMG_0098.JPG"
    p2 = staged / "IMG_0154.JPG"
    img.save(p1)
    img.save(p2)

    renames = rename_staged_photos_from_paths([str(p1), str(p2)], staged)
    assert (staged / "1-IMG_0098.JPG").is_file()
    assert (staged / "2-IMG_0154.JPG").is_file()
    assert len(renames) == 2


def test_parse_nr_foto_column(tmp_path: Path) -> None:
    path = tmp_path / "sheet.xlsx"
    pd.DataFrame(
        [
            {
                "Local": "JD",
                "Núm.": 1,
                "Face": "Superior",
                "Anomalia": "Acúmulo",
                "Quant Fotos": 1,
                "Disp.": "Sim",
                "Cam inicial": 99,
                "Cam final": 99,
                "nr_foto": 98,
            }
        ]
    ).to_excel(path, index=False, sheet_name="db_ficha")

    anomalies, _ = parse_excel(path)
    assert anomalies[0].nr_foto == "98"
    assert anomalies[0].resolved_photo_token == "98"


def test_sequential_report_filename() -> None:
    assert sequential_report_filename(1, ".jpg") == "IMG_0001.jpg"
    assert sequential_report_filename(12, ".PNG") == "IMG_0012.PNG"


def test_ordered_report_filename() -> None:
    assert ordered_report_filename(1, Path("IMG_0098.JPG")) == "1-IMG_0098.JPG"
    assert ordered_report_filename(12, Path("E116K24471000136S.jpg")) == "12-E116K24471000136S.jpg"


def test_stage_report_images_nested_source_folder(tmp_path: Path) -> None:
    """Fotos em subpasta (como após upload desktop)."""
    src_root = tmp_path / "input_images"
    nested = src_root / "MinhaObra"
    nested.mkdir(parents=True)
    img = PILImage.new("RGB", (10, 10), color=(1, 2, 3))
    img.save(nested / "E116K24471000136S.jpg")

    dest = tmp_path / "fotos_relatorio"
    anomalies = [
        Anomaly(
            local="VL1",
            number="1",
            face="Sup",
            anomaly_type="Fissura",
            image_range_start="00136",
            image_range_end="00136",
            nr_foto="00136",
            images=[str(nested / "E116K24471000136S.jpg")],
        ),
    ]

    updated, _ = stage_report_images(anomalies, src_root, dest)
    assert dest.is_dir()
    staged = list(dest.iterdir())
    assert len(staged) >= 1
    assert updated[0].images
    assert Path(updated[0].images[0]).is_file()
