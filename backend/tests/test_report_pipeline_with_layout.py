"""Geração de relatório respeitando photo_layout do frontend."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from backend.api import workspace as ws
from backend.api.server import app
from backend.core.parser_excel import parse_excel
from backend.core.photo_generator import build_photo_entry
from backend.core.photo_layout import PhotoLayoutEntry, materialize_anomalies_from_layout
from backend.services.report_pipeline import ReportConfig, generate_report


def test_generate_report_with_reordered_layout_and_custom_legend(
    sample_excel,
    sample_images,
    sample_template,
    output_dir,
) -> None:
    base_anomalies, _ = parse_excel(sample_excel)
    assert len(base_anomalies) >= 3

    by_row = {a.row_index: a for a in base_anomalies if a.row_index is not None}
    row_keys = sorted(by_row)
    row_a_key, row_c_key, row_b_key = row_keys[0], row_keys[1], row_keys[2]
    anomaly_a = by_row[row_a_key]
    anomaly_b = by_row[row_b_key]
    anomaly_c = by_row[row_c_key]

    token_a = anomaly_a.resolved_photo_token
    token_b = anomaly_b.resolved_photo_token
    token_c = anomaly_c.resolved_photo_token

    custom_legend = "Legenda personalizada na revisão fotográfica"
    photo_layout = [
        {
            "anomaly_id": f"anomaly-{row_c_key}",
            "row_index": row_c_key,
            "selected_photo": token_c,
            "legend": custom_legend,
        },
        {
            "anomaly_id": f"anomaly-{row_a_key}",
            "row_index": row_a_key,
            "selected_photo": token_a,
        },
    ]

    config = ReportConfig(
        excel_path=sample_excel,
        images_dir=sample_images,
        template_path=sample_template,
        output_dir=output_dir,
        bridge_id="E116",
        photo_km="244710",
        photo_layout=photo_layout,
    )
    result = generate_report(config)

    assert result.output_path.exists()
    assert len(result.report.anomalies) == 2
    assert result.report.photo_report is not None
    assert result.report.photo_report.total_photos == 2

    entries = result.report.photo_report.ordered_entries
    assert entries[0].description_line == f"{custom_legend}."
    assert entries[1].anomaly_row_index == row_a_key

    entry = build_photo_entry(
        result.report.anomalies[0],
        entries[0].image_path,
        1,
        1,
        "Ponte teste",
        report_code=entries[0].code,
    )
    assert custom_legend in entry.description_line


def test_materialize_reorders_relative_to_excel(sample_excel) -> None:
    base_anomalies, _ = parse_excel(sample_excel)
    rows = sorted(a.row_index for a in base_anomalies if a.row_index is not None)
    assert len(rows) >= 2

    first, second = rows[0], rows[1]
    layout = [
        PhotoLayoutEntry(
            anomaly_id=f"anomaly-{second}",
            row_index=second,
            selected_photo=next(a for a in base_anomalies if a.row_index == second).resolved_photo_token,
        ),
        PhotoLayoutEntry(
            anomaly_id=f"anomaly-{first}",
            row_index=first,
            selected_photo=next(a for a in base_anomalies if a.row_index == first).resolved_photo_token,
        ),
    ]
    ordered = materialize_anomalies_from_layout(base_anomalies, layout)
    assert [a.row_index for a in ordered] == [second, first]


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


def _seed_project_workspace(project_id: str, sample_excel, sample_images) -> None:
    ws.ensure_workspace(project_id)
    shutil.copy2(sample_excel, ws.excel_path(project_id))
    ws.clear_images(project_id)
    for image in sample_images.glob("*.jpg"):
        shutil.copy2(image, ws.images_dir(project_id) / image.name)


def test_generate_api_applies_photo_layout(
    api_client: TestClient,
    sample_excel,
    sample_images,
    sample_template,
) -> None:
    project_id = "layout-api-ok"
    _seed_project_workspace(project_id, sample_excel, sample_images)

    payload = {
        "name": "Ponte Teste",
        "rodovia": "BR-116",
        "km": "244+710",
        "bridge_id": "E116",
        "photo_km": "244710",
        "photo_direction": "S",
        "title": "Relatório de Inspeção — Ponte Teste",
    }

    analyze = api_client.post(f"/api/projects/{project_id}/analyze", json=payload)
    assert analyze.status_code == 200
    analysis = analyze.json()
    assert analysis["photos"]

    first = analysis["photos"][0]
    anomaly = next(a for a in analysis["anomalies"] if a["id"] == first["anomalyId"])
    custom_legend = "Legenda vinda da API de análise"

    generate_payload = {
        **payload,
        "photo_layout": [
            {
                "anomaly_id": anomaly["id"],
                "row_index": anomaly["rowIndex"],
                "selected_photo": anomaly["selectedPhotoNumber"],
                "legend": custom_legend,
            }
        ],
        "selected_photos": {anomaly["id"]: anomaly["selectedPhotoNumber"]},
    }

    response = api_client.post(f"/api/projects/{project_id}/generate", json=generate_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["photoCount"] == 1


def test_generate_api_rejects_partial_layout(
    api_client: TestClient,
    sample_excel,
    sample_images,
) -> None:
    project_id = "layout-api-422"
    _seed_project_workspace(project_id, sample_excel, sample_images)

    payload = {
        "name": "Ponte Teste",
        "rodovia": "BR-116",
        "km": "244+710",
        "bridge_id": "E116",
        "photo_km": "244710",
        "photo_direction": "S",
    }

    assert api_client.post(f"/api/projects/{project_id}/analyze", json=payload).status_code == 200

    generate_payload = {
        **payload,
        "photo_layout": [
            {
                "anomaly_id": "anomaly-2",
                "row_index": 2,
                "selected_photo": "136",
            },
            {
                "anomaly_id": "ghost-entry",
                "row_index": 99999,
                "selected_photo": "1",
            },
        ],
    }

    response = api_client.post(f"/api/projects/{project_id}/generate", json=generate_payload)
    assert response.status_code == 422
