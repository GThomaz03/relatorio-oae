"""Testes de resolução de siglas estruturais e seed da legenda."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.config import ensure_user_data_layout
from backend.rules.legenda import (
    clear_legenda_cache,
    load_legenda,
    resolve_local_code,
    save_legenda_entries,
)
from backend.models.structure import parse_local_code


@pytest.fixture(autouse=True)
def _clear_legenda_cache_after() -> None:
    yield
    clear_legenda_cache()


def test_resolve_local_code_sigla_e_numero() -> None:
    assert resolve_local_code("VL1") == "VL"
    assert resolve_local_code("PISTA") == "PISTA"
    assert resolve_local_code("JD1") == "JD"


def test_resolve_local_code_por_rotulo_mc() -> None:
    assert resolve_local_code("Muro de Contenção") == "MC"
    assert resolve_local_code("muro de contencao") == "MC"


def test_resolve_local_code_laje() -> None:
    assert resolve_local_code("L") == "L"
    assert resolve_local_code("Laje") == "L"
    assert resolve_local_code("L2") == "L"


def test_resolve_local_code_desconhecido() -> None:
    assert resolve_local_code("") is None


def test_parse_local_code_alias() -> None:
    assert parse_local_code("LB2") == "LB"


def test_load_legenda_vazio_retorna_none_para_todos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml_path = tmp_path / "legenda.yaml"
    yaml_path.write_text("entries: {}\n", encoding="utf-8")
    monkeypatch.setattr("backend.rules.legenda.LEGENDA_YAML_PATH", yaml_path)
    clear_legenda_cache()
    assert load_legenda() == {}
    assert resolve_local_code("JD") is None
    assert resolve_local_code("PISTA") is None


def test_ensure_user_data_layout_seeds_legenda(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    monkeypatch.setenv("OAE_DATA_DIR", str(data_dir))
    rules_src = Path(__file__).resolve().parents[1] / "rules" / "legenda.yaml"
    assert rules_src.is_file(), "backend/rules/legenda.yaml deve existir no repositório"

    import backend.config as cfg

    cfg._resolve_paths()
    ensure_user_data_layout()
    clear_legenda_cache()

    legenda_path = data_dir / "rules" / "legenda.yaml"
    assert legenda_path.is_file()
    assert len(load_legenda()) >= 50


def test_rio_goiabal_locais_com_legenda_completa() -> None:
    """Fixture conceitual: locais típicos do Rio Goiabal com legenda do repo."""
    clear_legenda_cache()
    for local, expected in (
        ("JD", "JD"),
        ("PISTA", "PISTA"),
        ("VL1", "VL"),
        ("Muro de Contenção", "MC"),
    ):
        assert resolve_local_code(local) == expected, local
    assert resolve_local_code("L") == "L"
