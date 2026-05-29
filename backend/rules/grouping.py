"""Regras de agrupamento e ordenação de anomalias."""

from __future__ import annotations

import re

from backend.models.anomaly import Anomaly
from backend.models.structure import format_local_with_number, parse_local_code
from backend.rules.anomaly_parser import (
    clean_anomaly_type,
    normalize_anomaly_type,
    parse_anomaly_text,
    resolve_template_key,
)
from backend.rules.photo_section_order import (
    build_anomaly_photo_sort_key,
    build_local_photo_sort_key,
)

__all__ = [
    "clean_anomaly_type",
    "normalize_anomaly_type",
    "parse_anomaly_text",
    "resolve_template_key",
    "grouping_key",
    "layout_merge_id",
    "anomaly_report_sort_key",
]


def structural_prefix(local: str) -> str | None:
    return parse_local_code(local)


def _span_grouping_token(span: str | None) -> str | None:
    if not span:
        return None
    span_text = str(span).strip()
    if not span_text:
        return None
    if span_text.lower().startswith("vão"):
        match = re.search(r"vão\s*(.+)", span_text, re.IGNORECASE)
        token = match.group(1) if match else span_text
    elif span_text.upper().startswith("V") and span_text[1:].isdigit():
        token = span_text[1:]
    else:
        token = span_text
    return token.strip() or None


def layout_merge_id(anomaly: Anomaly) -> str:
    """Agrupa original e duplicatas fotográficas na mesma entrada do relatório de anomalias."""
    if anomaly.source_anomaly_client_id:
        return anomaly.source_anomaly_client_id
    return anomaly.client_id or ""


def grouping_key(anomaly: Anomaly) -> tuple[str, str | None, str | None, str, str | None, str]:
    """
    Chave semântica normalizada + contexto estrutural (face, elemento, vão, família de duplicata).

    A legenda (view) não entra na chave — duplicatas com textos diferentes devem fundir-se.
    """
    prefix = structural_prefix(anomaly.local)
    element_id = format_local_with_number(anomaly.local, anomaly.number)
    type_key = (
        anomaly.semantics.grouping_key
        if anomaly.semantics
        else normalize_anomaly_type(anomaly.anomaly_type)
    )
    return (
        type_key,
        anomaly.face.strip().lower() if anomaly.face else None,
        prefix,
        element_id,
        _span_grouping_token(anomaly.span),
        layout_merge_id(anomaly),
    )


def group_key_label(key: tuple[str, str | None, str | None, str, str | None, str]) -> str:
    atype, face, prefix, element_id, _span, _merge = key
    parts = [atype]
    if prefix:
        parts.append(prefix)
    if element_id:
        parts.append(element_id)
    if face:
        parts.append(face)
    return "_".join(p for p in parts if p)


def element_number_sort_value(number: str | None) -> int:
    if not number:
        return 0
    match = re.search(r"(\d+)", str(number))
    return int(match.group(1)) if match else 0


def span_sort_value(span: str | None) -> int:
    if not span:
        return 0
    span_text = str(span).strip()
    if not span_text:
        return 0
    if span_text.lower().startswith("vão"):
        match = re.search(r"vão\s*(\S+)", span_text, re.IGNORECASE)
        token = match.group(1) if match else span_text
    elif span_text.upper().startswith("V") and span_text[1:].isdigit():
        token = span_text[1:]
    else:
        token = span_text
    return int(token) if token.isdigit() else 0


def anomaly_report_sort_key(anomaly: Anomaly) -> tuple[int, int, int, int, str, int, str]:
    """
    Ordem técnica do registro fotográfico (secção RSP, elemento, face, vão, tipo, linha).
    """
    return build_anomaly_photo_sort_key(
        anomaly,
        original_index=anomaly.row_index or 0,
    )


def sort_locals(locals_list: list[str]) -> list[str]:
    """Ordena locais pela sequência técnica do registro fotográfico."""
    return sorted(set(locals_list), key=build_local_photo_sort_key)
