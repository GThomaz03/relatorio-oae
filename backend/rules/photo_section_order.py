"""
Ordem técnica fixa do registro fotográfico (RSP).

Independente da ordem do Excel, upload ou processamento interno.
"""

from __future__ import annotations

import re
import unicodedata

from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup
from backend.models.structure import parse_local_code
from backend.rules.anomaly_parser import normalize_anomaly_type

# Ordem oficial do registro fotográfico (1 = primeiro)
PHOTO_SECTION_ORDER: dict[str, int] = {
    "laje": 1,
    "placas_pre_laje": 2,
    "lajes_balanco": 3,
    "vigas_longarinas": 4,
    "vigas_transversinas": 5,
    "aparelho_apoio": 6,
    "vigas_travessas": 7,
    "pilares": 8,
    "vigas_travamento": 9,
    "infraestrutura": 10,
    "encontros": 11,
    "cortinas": 12,
    "paredes": 13,
    "muros_ala": 14,
    "muros_contencao": 15,
    "taludes": 16,
    "pavimento_flexivel": 17,
    "juntas_dilatacao": 18,
    "barreiras_rigidas": 19,
    "guarda_corpos": 20,
    "placa_fechamento": 21,
    "defensa_metalica": 22,
    "sinalizacao": 23,
    "buzinotes": 24,
    "outros": 999,
}

PHOTO_SECTION_LABELS: dict[str, str] = {
    "laje": "Laje",
    "placas_pre_laje": "Placas de pré-laje",
    "lajes_balanco": "Lajes em balanço",
    "vigas_longarinas": "Vigas longarinas",
    "vigas_transversinas": "Vigas transversinas",
    "aparelho_apoio": "Aparelho de apoio",
    "vigas_travessas": "Vigas travessas",
    "pilares": "Pilares",
    "vigas_travamento": "Vigas de travamento",
    "infraestrutura": "Infraestrutura",
    "encontros": "Encontros",
    "cortinas": "Cortinas",
    "paredes": "Paredes",
    "muros_ala": "Muros de ala",
    "muros_contencao": "Muros de contenção",
    "taludes": "Taludes",
    "pavimento_flexivel": "Pavimento flexível",
    "juntas_dilatacao": "Juntas de dilatação",
    "barreiras_rigidas": "Barreiras rígidas",
    "guarda_corpos": "Guarda-corpos",
    "placa_fechamento": "Placa de fechamento",
    "defensa_metalica": "Defensa metálica",
    "sinalizacao": "Sinalização",
    "buzinotes": "Buzinotes",
    "outros": "Outros",
}

# Siglas RSP -> chave de secção fotográfica
CODE_TO_PHOTO_SECTION: dict[str, str] = {
    "L": "laje",
    "LS": "laje",
    "LI": "laje",
    "LT": "laje",
    "LAJE": "laje",
    "PPL": "placas_pre_laje",
    "PLP": "placas_pre_laje",
    "LB": "lajes_balanco",
    "BL": "lajes_balanco",
    "VL": "vigas_longarinas",
    "VLR": "vigas_longarinas",
    "VLT": "vigas_longarinas",
    "VT": "vigas_transversinas",
    "AA": "aparelho_apoio",
    "AP": "aparelho_apoio",
    "VTR": "vigas_travessas",
    "P": "pilares",
    "PIL": "pilares",
    "VTRAV": "vigas_travamento",
    "ET": "infraestrutura",
    "SAP": "infraestrutura",
    "TUB": "infraestrutura",
    "BLC": "infraestrutura",
    "BÇ": "infraestrutura",
    "CEL": "infraestrutura",
    "TRE": "infraestrutura",
    "AB": "infraestrutura",
    "AD": "infraestrutura",
    "AC": "infraestrutura",
    "ENC": "encontros",
    "EB": "encontros",
    "CO": "cortinas",
    "PA": "paredes",
    "AL": "muros_ala",
    "MC": "muros_contencao",
    "TA": "taludes",
    "PF": "pavimento_flexivel",
    "PISTA": "pavimento_flexivel",
    "PR": "pavimento_flexivel",
    "PC": "pavimento_flexivel",
    "PS": "pavimento_flexivel",
    "JD": "juntas_dilatacao",
    "BR": "barreiras_rigidas",
    "GC": "guarda_corpos",
    "GR": "guarda_corpos",
    "PLF": "placa_fechamento",
    "DM": "defensa_metalica",
    "SH": "sinalizacao",
    "SV": "sinalizacao",
    "BUZ": "buzinotes",
}

# Aliases textuais normalizados (substring match no campo Local)
LABEL_ALIAS_TO_SECTION: tuple[tuple[str, str], ...] = (
    ("placa de fechamento", "placa_fechamento"),
    ("placas de pre laje", "placas_pre_laje"),
    ("placa de pre laje", "placas_pre_laje"),
    ("pre laje", "placas_pre_laje"),
    ("laje em balanco", "lajes_balanco"),
    ("laje balanco", "lajes_balanco"),
    ("viga longarina", "vigas_longarinas"),
    ("viga transversina", "vigas_transversinas"),
    ("viga travessa", "vigas_travessas"),
    ("viga de travamento", "vigas_travamento"),
    ("aparelho de apoio", "aparelho_apoio"),
    ("muro de ala", "muros_ala"),
    ("muro de contencao", "muros_contencao"),
    ("pavimento flexivel", "pavimento_flexivel"),
    ("junta de dilatacao", "juntas_dilatacao"),
    ("barreira rigida", "barreiras_rigidas"),
    ("guarda corpo", "guarda_corpos"),
    ("guarda corpos", "guarda_corpos"),
    ("defensa metalica", "defensa_metalica"),
    ("sinalizacao", "sinalizacao"),
    ("buzinote", "buzinotes"),
    ("pilar", "pilares"),
    ("pilone", "pilares"),
    ("encontro", "encontros"),
    ("cortina", "cortinas"),
    ("parede", "paredes"),
    ("talude", "taludes"),
    ("estaca", "infraestrutura"),
    ("sapata", "infraestrutura"),
    ("tubulao", "infraestrutura"),
    ("bloco de fundacao", "infraestrutura"),
    ("berco", "infraestrutura"),
    ("trelica", "infraestrutura"),
    ("laje", "laje"),
)

# Aliases mais longos primeiro (evita "laje" capturar "laje em balanco")
_LABEL_ALIASES_SORTED: tuple[tuple[str, str], ...] = tuple(
    sorted(LABEL_ALIAS_TO_SECTION, key=lambda item: len(item[0]), reverse=True)
)

FACE_ORDER: dict[str, int] = {
    "superior": 1,
    "inferior": 2,
    "norte": 3,
    "sul": 4,
    "leste": 5,
    "oeste": 6,
    "nascente": 7,
    "poente": 8,
    "montante": 9,
    "jusante": 10,
    "extradorso": 11,
    "intradorso": 12,
    "sobre a obra": 13,
}


def normalize_match_key(text: str) -> str:
    """Normaliza texto para comparação (sem acentos, minúsculas)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def photo_section_rank(section: str) -> int:
    return PHOTO_SECTION_ORDER.get(section, PHOTO_SECTION_ORDER["outros"])


def resolve_photo_section(local: str, code: str | None = None) -> str:
    """Resolve chave de secção fotográfica a partir de Local e/ou sigla."""
    token = str(local or "").strip()
    token_upper = token.upper()
    if token_upper in CODE_TO_PHOTO_SECTION:
        return CODE_TO_PHOTO_SECTION[token_upper]

    parsed = (code or parse_local_code(token) or "").upper()
    if parsed and parsed in CODE_TO_PHOTO_SECTION:
        return CODE_TO_PHOTO_SECTION[parsed]

    normalized = normalize_match_key(token)
    for alias, section in _LABEL_ALIASES_SORTED:
        if alias in normalized:
            return section

    return "outros"


def face_sort_value(face: str | None) -> int:
    if not face or not str(face).strip():
        return 50
    key = normalize_match_key(face)
    return FACE_ORDER.get(key, 50)


def _element_number_sort_value(number: str | None) -> int:
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


def element_number_from_local(local: str, number: str | None) -> int:
    num = _element_number_sort_value(number)
    if num:
        return num
    match = re.search(r"(\d+)", str(local or ""))
    return int(match.group(1)) if match else 0


def build_anomaly_photo_sort_key(
    anomaly: Anomaly,
    *,
    original_index: int | None = None,
) -> tuple[int, int, int, int, str, int, str]:
    """
    Chave determinística para ordenação fotográfica.

    1. secção técnica (ordem RSP)
    2. número do elemento
    3. face
    4. vão
    5. tipo de anomalia (normalizado)
    6. índice original (planilha)
    7. local (desempate estável)
    """
    code = parse_local_code(anomaly.local)
    section = resolve_photo_section(anomaly.local, code)
    row_index = original_index if original_index is not None else (anomaly.row_index or 0)
    type_key = (
        anomaly.semantics.grouping_key
        if anomaly.semantics
        else normalize_anomaly_type(anomaly.anomaly_type)
    )
    return (
        photo_section_rank(section),
        element_number_from_local(anomaly.local, anomaly.number),
        face_sort_value(anomaly.face),
        span_sort_value(anomaly.span),
        type_key,
        row_index,
        str(anomaly.local or "").upper(),
    )


def build_group_photo_sort_key(group: AnomalyGroup) -> tuple[int, int, int, int, str, int, str]:
    if group.members:
        return min(
            build_anomaly_photo_sort_key(m, original_index=m.row_index or 0)
            for m in group.members
        )
    local = group.locals[0] if group.locals else ""
    code = group.structural_prefix
    section = resolve_photo_section(local, code)
    return (
        photo_section_rank(section),
        element_number_from_local(local, None),
        0,
        0,
        "",
        0,
        str(local).upper(),
    )


def build_local_photo_sort_key(local: str) -> tuple[int, int, str]:
    section = resolve_photo_section(local, parse_local_code(local))
    return (
        photo_section_rank(section),
        element_number_from_local(local, None),
        str(local).upper(),
    )


def sort_anomalies_for_photo_report(anomalies: list[Anomaly]) -> list[Anomaly]:
    """Ordena anomalias para relatório fotográfico e numeração RSP."""
    indexed = list(enumerate(anomalies))
    indexed.sort(
        key=lambda pair: build_anomaly_photo_sort_key(
            pair[1],
            original_index=pair[1].row_index if pair[1].row_index is not None else pair[0],
        ),
    )
    return [a for _, a in indexed]


def sort_groups_for_photo_report(groups: list[AnomalyGroup]) -> list[AnomalyGroup]:
    """Ordena grupos na sequência técnica do registro fotográfico."""
    return sorted(groups, key=build_group_photo_sort_key)


def sort_members_for_photo_report(members: list[Anomaly]) -> list[Anomaly]:
    return sorted(
        members,
        key=lambda m: build_anomaly_photo_sort_key(m, original_index=m.row_index or 0),
    )
