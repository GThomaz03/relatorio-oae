"""Parser semântico de anomalias — normalização, bases e modificadores."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from backend.config import RULES_DIR
from backend.models.anomaly_semantics import AnomalySemantics
logger = logging.getLogger(__name__)

CATALOG_PATH = RULES_DIR / "anomaly_catalog.yaml"

# Prefixo numérico DNIT (ex.: 1.10 - )
ANOMALY_CODE_PREFIX = re.compile(r"^\d+(?:\.\d+)*\s*-\s*")

CONNECTOR_SPLIT_RE = re.compile(r"\s+(?:,|;|\be\b)\s+", re.IGNORECASE)
CONNECTOR_PREFIX_RE = re.compile(r"^(?:com|c/|c\.?/)\s+", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class _CatalogEntry:
    key: str
    label: str
    template_key: str | None
    aliases_norm: tuple[str, ...]


@dataclass(frozen=True)
class _ModifierEntry:
    key: str
    label: str
    aliases_norm: tuple[str, ...]


def clean_anomaly_type(anomaly_type: str) -> str:
    """Remove código DNIT (ex.: '1.10 - Fissuras...' -> 'Fissuras...')."""
    return ANOMALY_CODE_PREFIX.sub("", anomaly_type.strip()).strip()


def normalize_for_match(text: str) -> str:
    """
    Normaliza texto para comparação semântica:
    minúsculas, sem acentos, espaços colapsados, conectores padronizados.
    """
    text = clean_anomaly_type(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace("c/", " com ")
    text = text.replace("c /", " com ")
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_anomaly_type(anomaly_type: str) -> str:
    """Chave snake_case derivada do texto (fallback)."""
    text = normalize_for_match(anomaly_type)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clear_catalog_cache() -> None:
    _load_catalog.cache_clear()


@lru_cache(maxsize=1)
def _load_catalog() -> tuple[list[_CatalogEntry], list[_ModifierEntry]]:
    path = CATALOG_PATH
    if not path.is_file():
        logger.warning("Catálogo de anomalias ausente: %s", path)
        return [], []

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    bases: list[_CatalogEntry] = []
    for key, entry in (raw.get("bases") or {}).items():
        if not isinstance(entry, dict):
            continue
        aliases = [str(a) for a in (entry.get("aliases") or [])]
        label = str(entry.get("label") or key).strip()
        aliases_norm = tuple(
            sorted({normalize_for_match(a) for a in [label, *aliases] if a}, key=len, reverse=True)
        )
        bases.append(
            _CatalogEntry(
                key=str(key),
                label=label,
                template_key=str(entry.get("template_key") or key),
                aliases_norm=aliases_norm,
            )
        )

    modifiers: list[_ModifierEntry] = []
    for key, entry in (raw.get("modifiers") or {}).items():
        if not isinstance(entry, dict):
            continue
        aliases = [str(a) for a in (entry.get("aliases") or [])]
        label = str(entry.get("label") or key).strip()
        aliases_norm = tuple(
            sorted({normalize_for_match(a) for a in [label, *aliases] if a}, key=len, reverse=True)
        )
        modifiers.append(
            _ModifierEntry(
                key=str(key),
                label=label,
                aliases_norm=aliases_norm,
            )
        )

    bases.sort(key=lambda b: max((len(a) for a in b.aliases_norm), default=0), reverse=True)
    modifiers.sort(key=lambda m: max((len(a) for a in m.aliases_norm), default=0), reverse=True)
    return bases, modifiers


def _longest_alias_match(
    text_norm: str,
    entries: list[_CatalogEntry] | list[_ModifierEntry],
) -> tuple[str, str, int, int] | None:
    best: tuple[str, str, int, int] | None = None
    for entry in entries:
        label = entry.label
        key = entry.key
        for alias in entry.aliases_norm:
            if not alias:
                continue
            idx = text_norm.find(alias)
            if idx < 0:
                continue
            span = (idx, idx + len(alias))
            if best is None or (span[1] - span[0]) > (best[3] - best[2]):
                best = (key, label, span[0], span[1])
    return best


def _strip_connectors(text: str) -> str:
    cleaned = text.strip()
    while cleaned:
        updated = CONNECTOR_PREFIX_RE.sub("", cleaned, count=1).strip()
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


def _extract_modifiers(remainder_norm: str, modifiers: list[_ModifierEntry]) -> tuple[list[str], list[str]]:
    if not remainder_norm.strip():
        return [], []

    segments = [_strip_connectors(part) for part in CONNECTOR_SPLIT_RE.split(remainder_norm)]
    segments = [s for s in segments if s]

    if not segments:
        segments = [_strip_connectors(remainder_norm)]

    keys: list[str] = []
    labels: list[str] = []
    seen: set[str] = set()

    for segment in segments:
        match = _longest_alias_match(segment, modifiers)
        if match:
            key, label, _, _ = match
            if key not in seen:
                seen.add(key)
                keys.append(key)
                labels.append(label)
            continue

        if segment and segment not in seen:
            fallback_key = normalize_anomaly_type(segment)
            seen.add(fallback_key)
            keys.append(fallback_key)
            labels.append(segment)

    return keys, labels


def _compose_formatted_label(base_label: str, modifier_labels: list[str]) -> str:
    if not modifier_labels:
        return base_label
    if len(modifier_labels) == 1:
        return f"{base_label} com {modifier_labels[0]}"
    return f"{base_label} com {' e '.join(modifier_labels)}"


def _build_grouping_key(base_key: str, modifier_keys: list[str]) -> str:
    if not modifier_keys:
        return base_key
    return "+".join([base_key, *sorted(modifier_keys)])


def parse_anomaly_text(anomaly_type: str) -> AnomalySemantics:
    """
    Identifica anomalia principal e complementos a partir do texto do Excel.

    Preserva o texto original e produz rótulo técnico formatado para o relatório.
    """
    original = anomaly_type.strip()
    normalized = normalize_for_match(original)
    bases, modifiers = _load_catalog()

    base_key = normalize_anomaly_type(original)
    base_label = clean_anomaly_type(original) or original
    template_key = base_key
    modifier_keys: list[str] = []
    modifier_labels: list[str] = []
    remainder = normalized

    base_match = _longest_alias_match(normalized, bases) if bases else None
    if base_match:
        base_key, base_label, start, end = base_match
        entry = next(b for b in bases if b.key == base_key)
        template_key = entry.template_key or base_key
        remainder = (normalized[:start] + normalized[end:]).strip()
        remainder = _strip_connectors(remainder)

    if remainder:
        mod_keys, mod_labels = _extract_modifiers(remainder, modifiers)
        modifier_keys.extend(mod_keys)
        modifier_labels.extend(mod_labels)

    formatted = _compose_formatted_label(base_label, modifier_labels)
    grouping_key = _build_grouping_key(base_key, modifier_keys)

    return AnomalySemantics(
        original_text=original,
        normalized_text=normalized,
        base_key=base_key,
        base_label=base_label,
        modifier_keys=modifier_keys,
        modifier_labels=modifier_labels,
        formatted_label=formatted,
        template_key=template_key,
        grouping_key=grouping_key,
    )


def resolve_template_key(anomaly_type: str) -> str:
    """Resolve chave do catálogo YAML de descrições."""
    return parse_anomaly_text(anomaly_type).template_key


def formatted_anomaly_label(anomaly_type: str) -> str:
    """Rótulo técnico formatado para relatório."""
    return parse_anomaly_text(anomaly_type).formatted_label
