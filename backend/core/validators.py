"""Validação de entradas e do relatório de inspeção."""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from backend.config import DOCX_EXTENSION, EXCEL_EXTENSION, IMAGE_EXTENSIONS
from backend.models.anomaly import Anomaly
from backend.models.inspection import InspectionReport

logger = logging.getLogger(__name__)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    severity: Severity
    code: str
    message: str
    row_index: int | None = None
    field: str | None = None

    @property
    def is_blocking(self) -> bool:
        return self.severity == Severity.ERROR


class ExcelStructureError(Exception):
    """Planilha Excel inválida ou incompleta."""

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class ImageNotFoundError(Exception):
    """Imagem referenciada não encontrada na pasta."""

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class InvalidImageRangeError(Exception):
    """Intervalo de imagens inválido."""

    def __init__(self, start: str, end: str, reason: str) -> None:
        super().__init__(f"Intervalo inválido ({start} até {end}): {reason}")
        self.start = start
        self.end = end
        self.reason = reason


def validate_file_extension(path: Path, allowed: set[str], label: str) -> ValidationIssue | None:
    if path.suffix.lower() not in allowed:
        return ValidationIssue(
            severity=Severity.ERROR,
            code="invalid_file_format",
            message=f"{label} deve ter extensão {', '.join(sorted(allowed))}, recebido: {path.suffix}",
        )
    return None


def validate_excel_path(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not path.exists():
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="file_not_found",
                message=f"Arquivo Excel não encontrado: {path}",
            )
        )
        return issues
    issue = validate_file_extension(path, {EXCEL_EXTENSION}, "Planilha Excel")
    if issue:
        issues.append(issue)
    return issues


def validate_images_dir(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not path.exists():
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="dir_not_found",
                message=f"Pasta de imagens não encontrada: {path}",
            )
        )
        return issues
    if not path.is_dir():
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="not_a_directory",
                message=f"Caminho de imagens não é um diretório: {path}",
            )
        )
    return issues


def validate_template_path(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not path.exists():
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="template_not_found",
                message=f"Template Word não encontrado: {path}",
            )
        )
        return issues
    issue = validate_file_extension(path, {DOCX_EXTENSION}, "Template Word")
    if issue:
        issues.append(issue)
    return issues


def validate_missing_columns(found: set[str], required: tuple[str, ...]) -> list[ValidationIssue]:
    missing = [col for col in required if col not in found]
    if not missing:
        return []
    return [
        ValidationIssue(
            severity=Severity.ERROR,
            code="missing_columns",
            message=f"Colunas obrigatórias ausentes na planilha: {', '.join(missing)}",
            field=missing[0],
        )
    ]


def validate_anomaly_images(anomaly: Anomaly, strict: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not anomaly.image_range_start or not anomaly.image_range_end:
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="missing_image_range",
                message="Cam inicial e Cam final são obrigatórios",
                row_index=anomaly.row_index,
            )
        )
        return issues

    if not anomaly.images:
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR if strict else Severity.WARNING,
                code="images_not_mapped",
                message=(
                    f"Nenhuma imagem mapeada para {anomaly.local} "
                    f"(intervalo {anomaly.image_range_start}–{anomaly.image_range_end})"
                ),
                row_index=anomaly.row_index,
            )
        )
    elif anomaly.photo_count_expected is not None and len(anomaly.images) != anomaly.photo_count_expected:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="photo_count_mismatch",
                message=(
                    f"Quant Fotos ({anomaly.photo_count_expected}) difere do mapeado "
                    f"({len(anomaly.images)}) em {anomaly.local}"
                ),
                row_index=anomaly.row_index,
            )
        )
    return issues


def detect_duplicate_image_references(anomalies: list[Anomaly]) -> list[ValidationIssue]:
    """Detecta o mesmo arquivo de imagem referenciado em múltiplas linhas."""
    path_to_rows: dict[str, list[int]] = {}
    issues: list[ValidationIssue] = []

    for anomaly in anomalies:
        for img_path in anomaly.images:
            row = anomaly.row_index or 0
            path_to_rows.setdefault(img_path, []).append(row)

    for img_path, rows in path_to_rows.items():
        if len(rows) > 1:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="duplicate_image_reference",
                    message=f"Imagem {Path(img_path).name} referenciada nas linhas {rows}",
                    row_index=rows[0],
                )
            )
    return issues


def validate_inspection(report: InspectionReport, strict: bool = False) -> list[ValidationIssue]:
    """Validação agregada pós-parse."""
    issues: list[ValidationIssue] = []
    issues.extend(validate_excel_path(report.metadata.excel_path))
    issues.extend(validate_images_dir(report.metadata.images_dir))
    issues.extend(validate_template_path(report.metadata.template_path))

    for anomaly in report.anomalies:
        issues.extend(validate_anomaly_images(anomaly, strict=strict))

    issues.extend(detect_duplicate_image_references(report.anomalies))

    errors = sum(1 for i in issues if i.is_blocking)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    logger.info(
        "Validação concluída: %d erro(s), %d aviso(s), %d anomalia(s)",
        errors,
        warnings,
        len(report.anomalies),
    )
    return issues


def raise_if_blocking(issues: list[ValidationIssue], strict: bool) -> None:
    """Interrompe o pipeline se houver erros (ou avisos em modo strict)."""
    blocking = [i for i in issues if i.is_blocking]
    if strict:
        blocking.extend(i for i in issues if i.severity == Severity.WARNING)

    if blocking:
        messages = "; ".join(i.message for i in blocking[:5])
        if len(blocking) > 5:
            messages += f" ... e mais {len(blocking) - 5}"
        raise ImageNotFoundError(
            f"Validação falhou ({len(blocking)} problema(s)): {messages}",
            issues=blocking,
        )
