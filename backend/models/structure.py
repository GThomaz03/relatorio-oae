"""Elementos estruturais e parsing de códigos em Local."""

from __future__ import annotations

import re

from backend.rules.legenda import load_legenda, resolve_local_code

# Ordem e hierarquia do relatório (modelo RSP)
MACRO_SECTION_ORDER: tuple[str, ...] = (
    "SUPERESTRUTURA",
    "MESOESTRUTURA",
    "INFRAESTRUTURA",
    "ENCONTRO",
    "PAVIMENTO",
    "JUNTA DE DILATAÇÃO",
    "SINALIZAÇÃO",
    "DISPOSITIVOS DE SEGURANÇA",
    "DRENAGEM",
    "GERAL",
)

# Macros cujo conteúdo aparece directamente sob o título (sem sub-Heading 4)
MACRO_WITHOUT_ELEMENT_SUBHEADING: frozenset[str] = frozenset(
    {
        "PAVIMENTO",
        "JUNTA DE DILATAÇÃO",
        "DRENAGEM",
        "SINALIZAÇÃO",
    }
)

PAVEMENT_CODES: frozenset[str] = frozenset({"PISTA", "PF", "PR", "PC"})

# Sigla -> macrosecção do relatório
MACRO_BY_CODE: dict[str, str] = {
    "VL": "SUPERESTRUTURA",
    "VLR": "SUPERESTRUTURA",
    "VLT": "SUPERESTRUTURA",
    "VT": "SUPERESTRUTURA",
    "VTR": "SUPERESTRUTURA",
    "VTRAV": "SUPERESTRUTURA",
    "L": "SUPERESTRUTURA",
    "LB": "SUPERESTRUTURA",
    "LS": "SUPERESTRUTURA",
    "LI": "SUPERESTRUTURA",
    "LT": "SUPERESTRUTURA",
    "BL": "SUPERESTRUTURA",
    "V": "SUPERESTRUTURA",
    "P": "MESOESTRUTURA",
    "PIL": "MESOESTRUTURA",
    "ET": "MESOESTRUTURA",
    "TUB": "MESOESTRUTURA",
    "SAP": "MESOESTRUTURA",
    "BLC": "MESOESTRUTURA",
    "JD": "JUNTA DE DILATAÇÃO",
    "BR": "DISPOSITIVOS DE SEGURANÇA",
    "GC": "DISPOSITIVOS DE SEGURANÇA",
    "GR": "DISPOSITIVOS DE SEGURANÇA",
    "DM": "DISPOSITIVOS DE SEGURANÇA",
    "BUZ": "DRENAGEM",
    "DR": "DRENAGEM",
    "VA": "DRENAGEM",
    "PF": "PAVIMENTO",
    "PR": "PAVIMENTO",
    "PC": "PAVIMENTO",
    "PISTA": "PAVIMENTO",
    "AL": "ENCONTRO",
    "CO": "ENCONTRO",
    "ENC": "ENCONTRO",
    "EB": "ENCONTRO",
    "MF": "ENCONTRO",
    "SH": "SINALIZAÇÃO",
    "SV": "SINALIZAÇÃO",
    "AA": "INFRAESTRUTURA",
    "AP": "INFRAESTRUTURA",
    "TA": "INFRAESTRUTURA",
}

# Preposição para redação técnica (no/na/em)
PREPOSITION_BY_CODE: dict[str, str] = {
    "P": "no",
    "PIL": "no",
    "AL": "no",
    "CO": "na",
    "MC": "no",
    "BUZ": "em",
    "PF": "no",
    "PR": "no",
    "PC": "no",
    "PISTA": "no",
    "JD": "na",
    "BR": "na",
    "GC": "na",
    "GR": "na",
    "DM": "na",
    "VL": "na",
    "VT": "na",
    "L": "na",
    "LB": "na",
    "LS": "na",
    "LI": "na",
    "LT": "na",
    "BL": "no",
    "V": "no",
    "ET": "na",
    "TUB": "no",
    "SAP": "na",
    "BLC": "no",
}

# Títulos de subsecção no relatório (Heading 4)
ELEMENT_HEADING_PT: dict[str, str] = {
    "P": "Pilares",
    "PIL": "Pilones",
    "VL": "Viga longarina",
    "VLR": "Viga longarina de rampa",
    "VLT": "Viga longarina de travessia",
    "VT": "Viga transversina",
    "VTR": "Viga travessa",
    "VTRAV": "Viga de travamento",
    "L": "Laje",
    "LB": "Laje em balanço",
    "LS": "Laje",
    "LI": "Laje",
    "LT": "Laje de transição",
    "BL": "Balanço longitudinal",
    "V": "Vão",
    "AL": "Muro de ala",
    "CO": "Cortinas",
    "BR": "Barreiras rígidas",
    "GC": "Guarda-corpos",
    "GR": "Guarda-rodas",
    "DM": "Defensa metálica",
    "BUZ": "Buzinotes",
    "JD": "Junta de dilatação",
    "PF": "Pavimento flexível",
    "PR": "Pavimento rígido",
    "PC": "Piso de concreto",
    "PISTA": "Pavimento flexível",
}

def parse_local_code(local: str) -> str | None:
    """Extrai sigla estrutural do campo Local (ex.: LB1 -> LB, PISTA -> PISTA)."""
    return resolve_local_code(local)


def is_pavement_code(code: str | None) -> bool:
    return code is not None and code.upper() in PAVEMENT_CODES


def structural_label_pt(code: str | None) -> str | None:
    if code is None:
        return None
    legenda = load_legenda()
    return legenda.get(code.upper(), code)


def _label_for_prose(label: str) -> str:
    """Remove qualificadores entre parênteses (ex.: 'Laje em balanço (transversal)')."""
    return re.sub(r"\s*\([^)]*\)", "", label).strip()


def structural_label_lower_pt(code: str | None) -> str | None:
    label = structural_label_pt(code)
    if not label:
        return None
    label = _label_for_prose(label)
    return label[0].lower() + label[1:]


def preposition_for_code(code: str | None) -> str:
    if code is None:
        return "na"
    return PREPOSITION_BY_CODE.get(code.upper(), "na")


def element_heading_for_code(code: str | None) -> str:
    """Título de subsecção para o relatório (Heading 4)."""
    if code is None:
        return "Outros"
    if code.upper() in ELEMENT_HEADING_PT:
        return ELEMENT_HEADING_PT[code.upper()]
    label = structural_label_pt(code)
    if label:
        clean = _label_for_prose(label)
        return clean[0].upper() + clean[1:] if clean else code
    return code


def hierarchy_for_code(code: str | None) -> tuple[str, str]:
    """Retorna (macrosecção, subsecção) para a sigla."""
    if code is None:
        return ("GERAL", "Outros")
    code = code.upper()
    macro = MACRO_BY_CODE.get(code, "GERAL")
    element = element_heading_for_code(code)
    return (macro, element)


def format_local_with_number(local: str, number: str | None = None) -> str:
    """
    Formata identificador do elemento (ex.: LB + 1 -> LB1).

    Se Local já contiver número (VL1), mantém como está.
    """
    local = str(local).strip()
    if re.search(r"\d", local):
        return local
    if number is None:
        return local
    num_text = str(number).strip()
    if not num_text or num_text.lower() == "nan":
        return local
    if num_text.endswith(".0") and num_text[:-2].isdigit():
        num_text = num_text[:-2]
    try:
        num_int = int(float(num_text))
        return f"{local}{num_int}"
    except ValueError:
        return local


def format_locals_list(locals_list: list[str]) -> str:
    """Formata lista de locais para texto (VL1 e VL2 / VL1, VL2 e VL3)."""
    if not locals_list:
        return ""
    if len(locals_list) == 1:
        return locals_list[0]
    if len(locals_list) == 2:
        return f"{locals_list[0]} e {locals_list[1]}"
    return ", ".join(locals_list[:-1]) + f" e {locals_list[-1]}"
