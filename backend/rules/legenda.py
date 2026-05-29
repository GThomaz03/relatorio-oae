"""Carrega e persiste siglas estruturais (legenda RSP)."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

from backend.config import RULES_DIR, data_root

LEGENDA_MD_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "legenda.md"
LEGENDA_YAML_PATH = RULES_DIR / "legenda.yaml"

_ENTRY_PATTERN = re.compile(
    r"^\s*-\s*\*\*(?P<code>[A-ZÇÁÉÍÓÚÃÕ]+)\*\*\s*[—–-]\s*(?P<label>.+?)\s*$",
    re.MULTILINE,
)


def _parse_markdown_legenda(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in _ENTRY_PATTERN.finditer(text):
        code = match.group("code").strip().upper()
        label = match.group("label").strip()
        result[code] = label
    return result


_LOCAL_ALIASES: dict[str, str] = {
    "MURO DE CONTENCAO": "MC",
    "LAJE": "L",
}


def _normalize_local_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip().upper()


def clear_legenda_cache() -> None:
    load_legenda.cache_clear()
    _legenda_label_index.cache_clear()


@lru_cache(maxsize=1)
def load_legenda(path: Path | None = None) -> dict[str, str]:
    """Retorna mapa SIGLA -> descrição (ex.: LB -> Laje em balanço)."""
    if path is not None:
        if path.suffix.lower() in {".yaml", ".yml"}:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict) and "entries" in raw and isinstance(raw["entries"], dict):
                return {str(k).upper(): str(v) for k, v in raw["entries"].items()}
            if isinstance(raw, dict):
                return {str(k).upper(): str(v) for k, v in raw.items() if k != "entries"}
        if path.is_file():
            return _parse_markdown_legenda(path.read_text(encoding="utf-8"))
        return {}

    yaml_path = LEGENDA_YAML_PATH
    if yaml_path.is_file():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict) and "entries" in raw and isinstance(raw["entries"], dict):
            return {str(k).upper(): str(v) for k, v in raw["entries"].items()}

    md_path = LEGENDA_MD_PATH
    if md_path.is_file():
        return _parse_markdown_legenda(md_path.read_text(encoding="utf-8"))

    bundle_md = data_root() / "data" / "legenda.md"
    if bundle_md.is_file():
        return _parse_markdown_legenda(bundle_md.read_text(encoding="utf-8"))

    return {}


def save_legenda_entries(entries: dict[str, str]) -> None:
    LEGENDA_YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": {k.upper(): v for k, v in sorted(entries.items())}}
    LEGENDA_YAML_PATH.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )


def legenda_codes_sorted() -> tuple[str, ...]:
    """Códigos ordenados do mais longo ao mais curto (match greedy)."""
    return tuple(sorted(load_legenda().keys(), key=len, reverse=True))


@lru_cache(maxsize=1)
def _legenda_label_index() -> dict[str, str]:
    """Mapa texto normalizado (rótulo ou alias) -> sigla."""
    index: dict[str, str] = {}
    for code, label in load_legenda().items():
        norm_label = _normalize_local_text(label)
        index[norm_label] = code
        clean = re.sub(r"\s*\([^)]*\)", "", norm_label).strip()
        if clean:
            index[clean] = code
    for alias, code in _LOCAL_ALIASES.items():
        index[_normalize_local_text(alias)] = code
    return index


def resolve_local_code(local: str) -> str | None:
    """
    Resolve sigla estrutural a partir do campo Local.

    Aceita sigla com número (VL1 -> VL), sigla isolada (PISTA) ou rótulo completo
    da legenda (ex.: 'Muro de Contenção' -> MC).
    """
    if not local or not str(local).strip():
        return None
    token = str(local).strip().upper()
    legenda = load_legenda()
    if token in legenda:
        return token
    for code in legenda_codes_sorted():
        if re.match(rf"^{re.escape(code)}(\d+)?$", token):
            return code
    norm = _normalize_local_text(local)
    return _legenda_label_index().get(norm)
