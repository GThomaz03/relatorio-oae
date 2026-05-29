"""Parser de planilhas Excel de inspeção OAE."""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from backend.config import (
    COLUMN_ALIASES,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
)
from backend.core.validators import (
    ExcelStructureError,
    Severity,
    ValidationIssue,
    validate_excel_path,
    validate_missing_columns,
)
from backend.models.anomaly import Anomaly

logger = logging.getLogger(__name__)

# Abas preferidas em planilhas PR-006-FOR-019 / banco de campo
PREFERRED_SHEET_NAMES: tuple[str, ...] = (
    "db_ficha",
    "DB_FICHA",
    "dados",
    "inspection",
    "anomalias",
)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _canonical_column_name(name: str) -> str:
    """Normaliza nomes de coluna (aliases, acentos, variações de encoding)."""
    raw = str(name).strip()
    if raw in COLUMN_ALIASES:
        return COLUMN_ALIASES[raw]

    key = _strip_accents(raw).lower()
    key = re.sub(r"\s+", " ", key)

    patterns: tuple[tuple[str, str], ...] = (
        (r"^local$", "Local"),
        (r"^num\.?$", "Núm."),
        (r"^n\.?m\.?$", "Núm."),
        (r"^face$", "Face"),
        (r"^vao/?ap", "Vão/AP"),
        (r"^vista$", "Vista"),
        (r"^anomalia$", "Anomalia"),
        (r"^w$", "W"),
        (r"^quant\.?$", "Quant."),
        (r"^comp\s*\(m\)$", "Comp (m)"),
        (r"^larg\s*\(m\)$", "Larg (m)"),
        (r"^quant\s*fotos$", "Quant Fotos"),
        (r"^disp\.?$", "Disp."),
        (r"^cam\s*inicial$", "Cam inicial"),
        (r"^cam\s*final$", "Cam final"),
        (r"^observa", "Observações"),
        (r"^area\s*m", "Área m²-m"),
        (r"^nr[_\s-]*foto$", "nr_foto"),
    )

    for pattern, canonical in patterns:
        if re.match(pattern, key):
            return canonical

    return raw


def _normalize_column_names(columns: pd.Index) -> list[str]:
    return [_canonical_column_name(col) for col in columns]


def _find_inspection_sheet(excel_path: Path, preferred: str | None = None) -> str:
    """Localiza aba com colunas de inspeção (ex.: db_ficha)."""
    xl = pd.ExcelFile(excel_path, engine="openpyxl")

    if preferred:
        if preferred not in xl.sheet_names:
            raise ExcelStructureError(
                f"Aba '{preferred}' não encontrada. Abas disponíveis: {', '.join(xl.sheet_names)}",
            )
        return preferred

    for candidate in PREFERRED_SHEET_NAMES:
        if candidate in xl.sheet_names:
            return candidate

    best_sheet = ""
    best_score = -1
    for sheet in xl.sheet_names:
        preview = pd.read_excel(excel_path, sheet_name=sheet, engine="openpyxl", nrows=3)
        cols = set(_normalize_column_names(preview.columns))
        score = sum(1 for col in REQUIRED_COLUMNS if col in cols)
        if score > best_score:
            best_score = score
            best_sheet = sheet

    if best_score < len(REQUIRED_COLUMNS):
        raise ExcelStructureError(
            "Nenhuma aba contém as colunas obrigatórias de inspeção. "
            f"Verifique se a planilha inclui a aba 'db_ficha' ou equivalente. "
            f"Abas encontradas: {', '.join(xl.sheet_names)}",
        )

    logger.info("Aba de inspeção detectada: %s (score=%d)", best_sheet, best_score)
    return best_sheet


def _load_dataframe(excel_path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    sheet = _find_inspection_sheet(excel_path, preferred=sheet_name)
    df = pd.read_excel(excel_path, sheet_name=sheet, engine="openpyxl")
    df.columns = _normalize_column_names(df.columns)
    return df


def _to_optional_str(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].replace("-", "").isdigit():
        text = text[:-2]
    return text if text else None


def _to_cam_str(value: object, width_hint: int = 3) -> str | None:
    """
    Normaliza referência de câmera/foto.

    Planilhas reais usam números sequenciais (98, 99, 100...) na aba db_ficha.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value))
    text = _to_optional_str(value)
    if not text:
        return None
    if text.isdigit():
        return text
    return text


def _cam_width_hint(start: object, end: object) -> int:
    hints: list[int] = []
    for val in (start, end):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            hints.append(len(str(int(val))))
            continue
        text = str(val).strip()
        if text.isdigit():
            hints.append(len(text))
    return max(hints) if hints else 3


def _to_optional_float(value: object, field: str, row_index: int) -> tuple[float | None, ValidationIssue | None]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None, None
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, ValidationIssue(
            severity=Severity.WARNING,
            code="invalid_numeric",
            message=f"Valor numérico inválido em '{field}': {value!r}",
            row_index=row_index,
            field=field,
        )


def _to_int_or_none(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _row_to_anomaly(row: pd.Series, row_index: int) -> tuple[Anomaly | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    local = _to_optional_str(row.get("Local"))
    number = _to_optional_str(row.get("Núm."))
    face = _to_optional_str(row.get("Face"))
    anomaly_type = _to_optional_str(row.get("Anomalia"))
    raw_cam_start = row.get("Cam inicial")
    raw_cam_end = row.get("Cam final")
    width = _cam_width_hint(raw_cam_start, raw_cam_end)
    cam_start = _to_cam_str(raw_cam_start, width_hint=width)
    cam_end = _to_cam_str(raw_cam_end, width_hint=width)

    if not all([local, face, anomaly_type, cam_start, cam_end]):
        missing = [
            name
            for name, val in [
                ("Local", local),
                ("Face", face),
                ("Anomalia", anomaly_type),
                ("Cam inicial", cam_start),
                ("Cam final", cam_end),
            ]
            if not val
        ]
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="missing_required_fields",
                message=f"Linha {row_index}: campos obrigatórios vazios: {', '.join(missing)}",
                row_index=row_index,
            )
        )
        return None, issues

    quantity, q_issue = _to_optional_float(row.get("Quant."), "Quant.", row_index)
    if q_issue:
        issues.append(q_issue)
    length, l_issue = _to_optional_float(row.get("Comp (m)"), "Comp (m)", row_index)
    if l_issue:
        issues.append(l_issue)
    width_val, w_issue = _to_optional_float(row.get("Larg (m)"), "Larg (m)", row_index)
    if w_issue:
        issues.append(w_issue)
    area, a_issue = _to_optional_float(row.get("Área m²-m"), "Área m²-m", row_index)
    if a_issue:
        issues.append(a_issue)

    nr_foto = _to_cam_str(row.get("nr_foto"))

    from backend.rules.anomaly_parser import parse_anomaly_text
    from backend.rules.legenda import resolve_local_code

    if local and resolve_local_code(local) is None:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="unknown_local",
                message=(
                    f"Local '{local}' não reconhecido na legenda — "
                    "revise sigla ou Gerenciamento > Siglas"
                ),
                row_index=row_index,
                field="Local",
            )
        )

    parsed_type = anomaly_type or ""
    semantics = parse_anomaly_text(parsed_type) if parsed_type else None

    anomaly = Anomaly(
        local=local or "",
        number=number,
        face=face or "",
        span=_to_optional_str(row.get("Vão/AP")),
        view=_to_optional_str(row.get("Vista")),
        anomaly_type=parsed_type,
        semantics=semantics,
        crack_width=_to_optional_str(row.get("W")),
        quantity=quantity,
        length=length,
        width=width_val,
        area=area,
        photo_count_expected=_to_int_or_none(row.get("Quant Fotos")),
        availability=_to_optional_str(row.get("Disp.")),
        observations=_to_optional_str(row.get("Observações")),
        nr_foto=nr_foto,
        image_range_start=cam_start or "",
        image_range_end=cam_end or "",
        row_index=row_index,
    )
    return anomaly, issues


def parse_excel(excel_path: Path, sheet_name: str | None = None) -> tuple[list[Anomaly], list[ValidationIssue]]:
    """
    Lê planilha .xlsx, valida estrutura e retorna anomalias normalizadas.

    Suporta planilhas multi-aba (ex.: PR-006-FOR-019 com aba ``db_ficha``).

    Raises:
        ExcelStructureError: se colunas obrigatórias estiverem ausentes ou arquivo inválido.
    """
    path_issues = validate_excel_path(excel_path)
    if any(i.is_blocking for i in path_issues):
        raise ExcelStructureError(
            path_issues[0].message,
            issues=path_issues,
        )

    from backend.rules.legenda import load_legenda

    logger.info("Lendo planilha Excel: %s", excel_path)

    df = _load_dataframe(excel_path, sheet_name=sheet_name)

    found_columns = set(df.columns)
    col_issues = validate_missing_columns(found_columns, REQUIRED_COLUMNS)
    if col_issues:
        raise ExcelStructureError(col_issues[0].message, issues=col_issues)

    for opt in OPTIONAL_COLUMNS:
        if opt not in df.columns:
            df[opt] = None

    anomalies: list[Anomaly] = []
    all_issues: list[ValidationIssue] = []
    if not load_legenda():
        logger.error("Legenda estrutural vazia ao parsear Excel")
        all_issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="legenda_not_loaded",
                message=(
                    "Legenda estrutural não carregada — verifique Gerenciamento > Siglas "
                    "ou reinstale o aplicativo"
                ),
            )
        )

    for idx, row in df.iterrows():
        row_index = int(idx) + 2  # cabeçalho + 1-based
        if row.isna().all():
            continue
        local_val = _to_optional_str(row.get("Local"))
        if local_val is None:
            continue

        anomaly, row_issues = _row_to_anomaly(row, row_index)
        all_issues.extend(row_issues)
        if anomaly is not None:
            anomalies.append(anomaly)

    logger.info(
        "Planilha parseada: %d linha(s) de anomalia, %d aviso(s)/erro(s) de linha",
        len(anomalies),
        len(all_issues),
    )
    return anomalies, all_issues
