"""Fixtures pytest para testes do gerador OAE."""

from __future__ import annotations

from pathlib import Path

import shutil

import pandas as pd
import pytest
from PIL import Image as PILImage

FIXTURES_DIR = Path(__file__).parent / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def sample_excel(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "inspection.xlsx"

    rows = [
        {
            "Local": "VL1",
            "Núm.": "1",
            "Face": "Superior",
            "Vão/AP": "V1",
            "Vista": "Extradorso",
            "Anomalia": "Fissura vertical",
            "W": "0,3 mm",
            "Quant.": 1,
            "Comp (m)": 2.5,
            "Larg (m)": None,
            "Quant Fotos": 3,
            "Disp.": "Sim",
            "Cam inicial": "00136",
            "Cam final": "00138",
            "nr_foto": "00136",
            "Observações": "Fissura ativa",
            "Área m²-m": None,
        },
        {
            "Local": "VL2",
            "Núm.": "2",
            "Face": "Superior",
            "Vão/AP": "V1",
            "Vista": "Extradorso",
            "Anomalia": "Fissura vertical",
            "W": "0,2 mm",
            "Quant.": 1,
            "Comp (m)": 1.8,
            "Larg (m)": None,
            "Quant Fotos": 1,
            "Disp.": "Sim",
            "Cam inicial": "00139",
            "Cam final": "00139",
            "nr_foto": None,
            "Observações": None,
            "Área m²-m": None,
        },
        {
            "Local": "P1",
            "Núm.": "3",
            "Face": "Norte",
            "Vão/AP": None,
            "Vista": None,
            "Anomalia": "Erosão",
            "W": None,
            "Quant.": 2,
            "Comp (m)": None,
            "Larg (m)": None,
            "Quant Fotos": 1,
            "Disp.": "Sim",
            "Cam inicial": "00140",
            "Cam final": "00140",
            "nr_foto": "00140",
            "Observações": "Perda de cobrimento",
            "Área m²-m": 0.5,
        },
    ]
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False, engine="openpyxl")
    return path


@pytest.fixture(scope="session")
def sample_images(fixtures_dir: Path) -> Path:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    tokens = ["00136", "00137", "00138", "00139", "00140"]
    for token in tokens:
        filename = IMAGES_DIR / f"E116K244710{token}S.jpg"
        if not filename.exists():
            img = PILImage.new("RGB", (80, 60), color=(120, 120, 120))
            img.save(filename, format="JPEG")
    return IMAGES_DIR


@pytest.fixture(scope="session")
def sample_template(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "report_template.docx"
    main_template = Path(__file__).resolve().parents[1] / "templates" / "report_template.docx"

    if main_template.is_file():
        shutil.copy2(main_template, path)
    elif not path.exists():
        pytest.skip("Template de referência indisponível para testes")

    return path


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture(autouse=True)
def _isolate_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Isola dados de runtime dos testes em diretório temporário."""
    from backend import config

    monkeypatch.setenv("OAE_DATA_DIR", str(tmp_path / "data"))
    config._resolve_paths()


@pytest.fixture(autouse=True)
def _seed_legenda_if_missing() -> None:
    """Evita legenda vazia em OAE_DATA_DIR de smoke tests anteriores."""
    from backend import config
    from backend.rules.legenda import clear_legenda_cache, load_legenda

    pkg_legenda = config.PACKAGE_ROOT / "rules" / "legenda.yaml"
    target = config.RULES_DIR / "legenda.yaml"
    if pkg_legenda.is_file():
        if not load_legenda() or "L" not in load_legenda():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pkg_legenda, target)
            clear_legenda_cache()
    yield
    clear_legenda_cache()
