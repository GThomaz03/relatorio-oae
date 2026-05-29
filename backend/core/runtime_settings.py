"""Configurações editáveis em runtime para geração de relatórios."""

from __future__ import annotations

import json
from pathlib import Path

from backend.config import RULES_DIR

RUNTIME_SETTINGS_PATH = RULES_DIR / "runtime_settings.json"

DEFAULT_RUNTIME_SETTINGS: dict[str, str] = {
    "default_report_title_template": "Relatório de Inspeção — {project_name}",
    "bridge_location_line_template": "{project_name} — {rodovia} — — Km {km} —",
    "photo_caption_template": "Fig. {figure_number} — {code} — {description_line}",
    "photo_direction": "S",
    "photo_seq_width": "3",
    "default_bridge_prefix": "E",
    "excel_preferred_sheet": "db_ficha",
}


def ensure_runtime_settings_file() -> None:
    if RUNTIME_SETTINGS_PATH.is_file():
        return
    RUNTIME_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_SETTINGS_PATH.write_text(
        json.dumps(DEFAULT_RUNTIME_SETTINGS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_runtime_settings() -> dict[str, str]:
    ensure_runtime_settings_file()
    try:
        raw = json.loads(RUNTIME_SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    merged = {**DEFAULT_RUNTIME_SETTINGS}
    for key, value in raw.items():
        if key in DEFAULT_RUNTIME_SETTINGS and isinstance(value, str):
            merged[key] = value
    return merged


def save_runtime_settings(settings: dict[str, str]) -> dict[str, str]:
    merged = {**DEFAULT_RUNTIME_SETTINGS}
    for key in DEFAULT_RUNTIME_SETTINGS:
        value = settings.get(key, DEFAULT_RUNTIME_SETTINGS[key])
        merged[key] = value if isinstance(value, str) else DEFAULT_RUNTIME_SETTINGS[key]

    ensure_runtime_settings_file()
    RUNTIME_SETTINGS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return merged


def render_template(template: str, context: dict[str, str], fallback: str) -> str:
    try:
        return template.format(**context)
    except KeyError:
        return fallback.format(**context)
