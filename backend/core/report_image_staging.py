"""Preparação e renomeação da pasta fotos_relatorio."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.config import REPORT_PHOTOS_DIR_NAME, SEQUENTIAL_IMG_WIDTH
from backend.core.parser_images import build_image_index, resolve_image_for_token
from backend.core.photo_numbering import PhotoAssignment
from backend.core.validators import Severity, ValidationIssue
from backend.models.anomaly import Anomaly

logger = logging.getLogger(__name__)


def report_photos_dir(output_dir: Path) -> Path:
    return output_dir / REPORT_PHOTOS_DIR_NAME


def ordered_report_filename(sequence: int, original_path: Path) -> str:
    """
    Nome na ordem do relatório preservando o identificador original.

    Ex.: 1-IMG_0098.JPG, 2-IMG_0154.JPG
    """
    ext = original_path.suffix or ".jpg"
    return f"{sequence}-{original_path.stem}{ext}"


def sequential_report_filename(sequence: int, suffix: str) -> str:
    """Alias legado — preferir ordered_report_filename."""
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    return f"IMG_{sequence:0{SEQUENTIAL_IMG_WIDTH}d}{ext}"


def stage_report_images(
    anomalies: list[Anomaly],
    source_dir: Path,
    dest_dir: Path,
) -> tuple[list[Anomaly], list[ValidationIssue]]:
    """
    Copia para dest_dir apenas as fotos utilizadas no relatório (sem duplicar).

    Cada anomalia referencia uma única imagem (nr_foto ou Cam inicial).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_index = build_image_index(source_dir)
    issues: list[ValidationIssue] = []
    updated: list[Anomaly] = []
    copied_sources: dict[str, str] = {}

    for anomaly in anomalies:
        token = anomaly.resolved_photo_token
        paths, token_issues = resolve_image_for_token(source_index, token)
        issues.extend(token_issues)

        if not paths:
            updated.append(anomaly.model_copy(update={"images": []}))
            continue

        source_path = paths[0]
        if source_path in copied_sources:
            staged_path = copied_sources[source_path]
        else:
            src = Path(source_path)
            staged_path = str(dest_dir / src.name)
            shutil.copy2(src, staged_path)
            copied_sources[source_path] = staged_path
            logger.debug("Copiada %s -> %s", src.name, staged_path)

        updated.append(anomaly.model_copy(update={"images": [staged_path]}))

    logger.info(
        "Pasta %s: %d arquivo(s) copiado(s) a partir de %d anomalia(s)",
        dest_dir.name,
        len(copied_sources),
        len(anomalies),
    )
    return updated, issues


def attach_staged_images(
    anomalies: list[Anomaly],
    staged_dir: Path,
) -> tuple[list[Anomaly], list[ValidationIssue]]:
    """Valida que as imagens staged existem e normaliza caminhos."""
    issues: list[ValidationIssue] = []
    updated: list[Anomaly] = []

    for anomaly in anomalies:
        valid_paths: list[str] = []
        token = anomaly.resolved_photo_token
        for image_path in anomaly.images:
            path = Path(image_path)
            if path.is_file():
                valid_paths.append(str(path.resolve()))
                continue
            candidate = staged_dir / path.name
            if candidate.is_file():
                valid_paths.append(str(candidate.resolve()))
                continue
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="staged_image_missing",
                    message=f"Imagem staged não encontrada para token {token}: {path.name}",
                    row_index=anomaly.row_index,
                )
            )

        updated.append(anomaly.model_copy(update={"images": valid_paths}))

    return updated, issues


def _rename_paths_in_order(image_paths: list[str], staged_dir: Path) -> dict[str, str]:
    """Renomeia arquivos para N-nome_original.ext na ordem do relatório."""
    renames: dict[str, str] = {}
    seen_sources: set[str] = set()
    temp_moves: list[tuple[Path, Path]] = []

    for image_path in image_paths:
        source = Path(image_path).resolve()
        source_key = str(source)
        if source_key in seen_sources:
            continue
        if not source.is_file():
            logger.warning("Arquivo não encontrado para renomeação: %s", source)
            continue

        seen_sources.add(source_key)
        temp_path = staged_dir / f"__tmp_{len(temp_moves) + 1:04d}{source.suffix}"
        temp_moves.append((source, temp_path))

    for old_path, temp_path in temp_moves:
        old_path.rename(temp_path)

    for idx, (old_path, temp_path) in enumerate(temp_moves, start=1):
        new_path = staged_dir / ordered_report_filename(idx, old_path)
        temp_path.rename(new_path)
        renames[str(old_path)] = str(new_path)

    return renames


def rename_staged_photos_sequential(
    assignments: list[PhotoAssignment],
    staged_dir: Path,
) -> dict[str, str]:
    """
    Renomeia arquivos em fotos_relatorio para IMG_0001, IMG_0002, …
    na ordem de aparição no relatório (sem duplicar renomeações).
    """
    if not staged_dir.is_dir():
        logger.warning("Pasta staged inexistente para renomeação: %s", staged_dir)
        return {}

    ordered_paths: list[str] = []
    seen: set[str] = set()
    for assignment in assignments:
        path = assignment.image_path
        if path and path not in seen:
            ordered_paths.append(path)
            seen.add(path)

    renames = _rename_paths_in_order(ordered_paths, staged_dir)
    logger.info(
        "Renomeação sequencial em %s: %d arquivo(s)",
        staged_dir.name,
        len(renames),
    )
    return renames


def rename_staged_photos_from_paths(
    image_paths: list[str],
    staged_dir: Path,
) -> dict[str, str]:
    """Renomeação sequencial a partir de lista ordenada de caminhos."""
    if not staged_dir.is_dir():
        return {}
    return _rename_paths_in_order(image_paths, staged_dir)
