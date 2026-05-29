"""Testes da API de gerenciamento."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from backend.api.server import app
from backend.config import DEFAULT_DESCRIPTIONS, RULES_DIR
from backend.rules.anomaly_parser import clear_catalog_cache


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_input_schema(client: TestClient) -> None:
    response = client.get("/api/management/input-schema")
    assert response.status_code == 200
    data = response.json()
    assert any(c["name"] == "Local" for c in data["required_columns"])
    assert "db_ficha" in data["default_sheet_names"]


def test_validate_excel_upload(client: TestClient, tmp_path) -> None:
    path = tmp_path / "test.xlsx"
    rows = [
        {
            "Local": "VL1",
            "Núm.": 1,
            "Face": "Superior",
            "Anomalia": "Fissura",
            "Quant Fotos": 1,
            "Disp.": "Sim",
            "Cam inicial": 136,
            "Cam final": 136,
        }
    ]
    pd.DataFrame(rows).to_excel(path, index=False, sheet_name="db_ficha")

    with path.open("rb") as handle:
        response = client.post(
            "/api/management/validate-excel",
            files={"file": ("test.xlsx", handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["sheet_name"] == "db_ficha"


def test_anomaly_catalog_round_trip(client: TestClient) -> None:
    original = client.get("/api/management/anomaly-catalog").json()
    payload = {
        "bases": [
            *original["bases"],
            {
                "key": "test_base_mgmt",
                "label": "Teste base",
                "template_key": "default",
                "aliases": ["texto teste base mgmt"],
            },
        ],
        "modifiers": original["modifiers"],
    }
    put = client.put("/api/management/anomaly-catalog", json=payload)
    assert put.status_code == 200
    clear_catalog_cache()

    preview = client.post(
        "/api/management/anomaly-catalog/preview",
        json={"anomaly_text": "texto teste base mgmt"},
    )
    assert preview.status_code == 200
    assert preview.json()["base_key"] == "test_base_mgmt"
    client.put("/api/management/anomaly-catalog", json=original)
    clear_catalog_cache()


def test_preview_description(client: TestClient) -> None:
    response = client.post(
        "/api/management/preview-description",
        json={
            "template": "{anomaly_type_clean} {prep} {structural_phrase}{face_part}",
            "sample_row": {"local": "LB", "anomalia": "Fissura vertical"},
        },
    )
    assert response.status_code == 200
    assert "rendered" in response.json()


def test_legenda_put_get(client: TestClient) -> None:
    original = client.get("/api/management/legenda").json()
    entries = list(original["entries"])
    entries.append({"code": "ZZT", "label": "Elemento teste"})
    put = client.put("/api/management/legenda", json={"entries": entries})
    assert put.status_code == 200
    get = client.get("/api/management/legenda")
    codes = [e["code"] for e in get.json()["entries"]]
    assert "ZZT" in codes
    client.put("/api/management/legenda", json=original)


def test_management_export_import(client: TestClient) -> None:
    export = client.get("/api/management/export")
    assert export.status_code == 200
    bundle = export.json()
    assert "runtime_settings" in bundle
    assert "description_rules" in bundle

    import_response = client.put(
        "/api/management/import",
        content=json.dumps(bundle).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert import_response.status_code == 200


def test_management_summary(client: TestClient) -> None:
    response = client.get("/api/management/summary")
    assert response.status_code == 200
    assert "checklist" in response.json()


def test_management_summary_legenda_checklist_fails_when_empty(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    empty_yaml = tmp_path / "legenda.yaml"
    empty_yaml.write_text("entries: {}\n", encoding="utf-8")
    monkeypatch.setattr("backend.rules.legenda.LEGENDA_YAML_PATH", empty_yaml)
    from backend.rules.legenda import clear_legenda_cache

    clear_legenda_cache()
    response = client.get("/api/management/summary")
    assert response.status_code == 200
    checklist = {item["id"]: item for item in response.json()["checklist"]}
    assert checklist["legenda"]["ok"] is False
