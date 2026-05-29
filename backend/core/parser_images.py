"""Parser e mapeamento de imagens de inspeção."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from backend.config import (
    CAM_TOKEN_PATTERN,
    IMAGE_CAM_OFFSET,
    IMAGE_EXTENSIONS,
    IMAGE_FILENAME_PATTERN,
    IMG_FILENAME_PATTERN,
    MAX_IMAGE_RANGE_SPAN,
)
from backend.core.validators import InvalidImageRangeError, Severity, ValidationIssue
from backend.models.anomaly import Anomaly
from backend.models.image import ImageDimensions, ImageFile

logger = logging.getLogger(__name__)


class ImageIndex(BaseModel):
    """Índice de imagens da pasta de inspeção."""

    by_name: dict[str, ImageFile] = Field(default_factory=dict)
    by_token: dict[str, list[ImageFile]] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def all_files(self) -> list[ImageFile]:
        seen: set[str] = set()
        result: list[ImageFile] = []
        for img in self.by_name.values():
            if img.path_str not in seen:
                seen.add(img.path_str)
                result.append(img)
        return result

_RANGE_SEPARATORS = re.compile(r"\s*(?:até|a|-|–|—)\s*", re.IGNORECASE)


def normalize_sequence_token(token: str) -> str:
    """Chave canónica para correspondência (00136, 000136 e 136 equivalem)."""
    stripped = token.strip().lstrip("0")
    return stripped or "0"


def token_lookup_keys(token: str) -> list[str]:
    """Gera variantes de token para índice e busca."""
    canonical = normalize_sequence_token(token)
    keys = {token.strip(), canonical}
    for width in (3, 4, 5, 6):
        keys.add(canonical.zfill(width))
    return list(keys)


def extract_numeric_token(value: str) -> str | None:
    """Extrai token numérico principal de Cam inicial/final ou nome de arquivo."""
    value = value.strip()
    if not value:
        return None
    match = CAM_TOKEN_PATTERN.search(value)
    if match:
        return match.group(1)
    if value.isdigit():
        return value
    return None


def _pad_width(start: str, end: str) -> int:
    return max(len(start), len(end), 3)


def expand_image_range(start: str, end: str) -> list[str]:
    """
    Expande intervalo numérico (spec §8.1).

    Ex.: 00136, 00138 -> ['00136', '00137', '00138']
    """
    start = start.strip()
    end = end.strip()

    start_num = extract_numeric_token(start)
    end_num = extract_numeric_token(end)

    if start_num is None or end_num is None:
        raise InvalidImageRangeError(
            start,
            end,
            "não foi possível extrair tokens numéricos",
        )

    start_int = int(start_num)
    end_int = int(end_num)

    if end_int < start_int:
        raise InvalidImageRangeError(start, end, "valor final menor que o inicial")

    span = end_int - start_int + 1
    if span > MAX_IMAGE_RANGE_SPAN:
        raise InvalidImageRangeError(
            start,
            end,
            f"intervalo excede o máximo permitido ({MAX_IMAGE_RANGE_SPAN})",
        )

    width = _pad_width(start_num, end_num)
    return [str(i).zfill(width) for i in range(start_int, end_int + 1)]


def parse_range_cell(value: str) -> tuple[str, str]:
    """Interpreta célula que pode conter intervalo embutido (ex.: '00136 até 00138')."""
    value = value.strip()
    parts = _RANGE_SEPARATORS.split(value)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return value, value


def _parse_filename(stem: str) -> tuple[str | None, str | None, str | None]:
    img_match = IMG_FILENAME_PATTERN.match(stem)
    if img_match:
        num = int(img_match.group("num"))
        return "IMG", str(num), None

    match = IMAGE_FILENAME_PATTERN.match(stem)
    if match:
        return match.group("prefix"), match.group("seq"), match.group("suffix")
    return None, None, None


def _load_dimensions(path: Path) -> ImageDimensions | None:
    try:
        with Image.open(path) as img:
            return ImageDimensions(width_px=img.width, height_px=img.height)
    except OSError:
        return None


def iter_image_files(images_dir: Path) -> list[Path]:
    """Lista arquivos de imagem recursivamente (inclui subpastas do upload)."""
    if not images_dir.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(images_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(path)
    return files


def count_image_files(images_dir: Path) -> int:
    return len(iter_image_files(images_dir))


def _register_image_in_index(
    path: Path,
    by_name: dict[str, ImageFile],
    by_token: dict[str, list[ImageFile]],
) -> None:
    prefix, seq, _suffix = _parse_filename(path.stem)
    image = ImageFile(
        filename=path.name,
        path=path.resolve(),
        stem=path.stem,
        suffix=path.suffix.lower(),
        sequence_token=seq,
        prefix=prefix,
        dimensions=_load_dimensions(path),
    )
    by_name[path.name.lower()] = image
    by_name[path.stem.lower()] = image
    if seq:
        for key in token_lookup_keys(seq):
            by_token.setdefault(key, []).append(image)
        if prefix == "IMG" and seq.isdigit():
            cam_token = str(int(seq) - IMAGE_CAM_OFFSET)
            for key in token_lookup_keys(cam_token):
                by_token.setdefault(key, []).append(image)


def build_image_index(images_dir: Path) -> ImageIndex:
    """Indexa todas as imagens da pasta por nome, stem e token numérico."""
    if not images_dir.is_dir():
        logger.warning("Pasta de imagens inexistente: %s", images_dir)
        return ImageIndex()

    by_name: dict[str, ImageFile] = {}
    by_token: dict[str, list[ImageFile]] = {}

    for path in iter_image_files(images_dir):
        _register_image_in_index(path, by_name, by_token)

    idx = ImageIndex(by_name=by_name, by_token=by_token)
    logger.info("Índice de imagens: %d arquivo(s) em %s", len(idx.all_files()), images_dir)
    return idx


def resolve_images_for_range(
    index: ImageIndex,
    start: str,
    end: str,
    prefix_hint: str | None = None,
) -> tuple[list[str], list[ValidationIssue]]:
    """Resolve tokens de intervalo para caminhos de arquivo existentes."""
    issues: list[ValidationIssue] = []
    start_clean, end_from_start = parse_range_cell(start)
    if end_from_start != start_clean:
        end_clean = end_from_start
    else:
        _, end_clean = parse_range_cell(end)
        if end_clean == end and end.strip():
            end_clean = end.strip()
    start_clean = start_clean.strip()
    end_clean = end_clean.strip()

    try:
        tokens = expand_image_range(start_clean, end_clean)
    except InvalidImageRangeError as exc:
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="invalid_image_range",
                message=str(exc),
            )
        )
        return [], issues

    resolved: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        candidates: list[ImageFile] = []
        for key in token_lookup_keys(token):
            candidates.extend(index.by_token.get(key, []))
        # Remover duplicados
        seen_paths: set[str] = set()
        unique: list[ImageFile] = []
        for img in candidates:
            if img.path_str not in seen_paths:
                seen_paths.add(img.path_str)
                unique.append(img)
        candidates = unique
        if prefix_hint and candidates:
            filtered = [c for c in candidates if c.prefix and prefix_hint.upper() in c.prefix.upper()]
            if filtered:
                candidates = filtered

        if not candidates:
            for img in index.all_files():
                if token in img.stem and img.path_str not in seen:
                    candidates = [img]
                    break

        if not candidates:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="image_not_found",
                    message=f"Imagem não encontrada para token {token} (intervalo {start}–{end})",
                )
            )
            continue

        chosen = sorted(candidates, key=lambda i: i.filename)[0]
        if chosen.path_str not in seen:
            resolved.append(chosen.path_str)
            seen.add(chosen.path_str)

    return resolved, issues


def resolve_image_for_token(
    index: ImageIndex,
    token: str,
    prefix_hint: str | None = None,
) -> tuple[list[str], list[ValidationIssue]]:
    """Resolve um único token (nr_foto ou Cam inicial) para caminho de arquivo."""
    issues: list[ValidationIssue] = []
    token = token.strip()
    if not token:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="empty_photo_token",
                message="Token de foto vazio (nr_foto e Cam inicial ausentes)",
            )
        )
        return [], issues

    candidates: list[ImageFile] = []
    lookup_keys = list(token_lookup_keys(token))
    if token.isdigit():
        offset_token = str(int(token) + IMAGE_CAM_OFFSET)
        lookup_keys.extend(token_lookup_keys(offset_token))

    seen_paths: set[str] = set()
    for key in lookup_keys:
        for img in index.by_token.get(key, []):
            if img.path_str not in seen_paths:
                candidates.append(img)
                seen_paths.add(img.path_str)

    if prefix_hint and candidates:
        filtered = [c for c in candidates if c.prefix and prefix_hint.upper() in c.prefix.upper()]
        if filtered:
            candidates = filtered

    if not candidates and token.isdigit():
        for ext in IMAGE_EXTENSIONS:
            for width in (4, 3, 5, 6):
                name = f"IMG_{int(token):0{width}d}{ext}"
                hit = index.by_name.get(name.lower())
                if hit and hit.path_str not in seen_paths:
                    candidates.append(hit)
                    seen_paths.add(hit.path_str)

    if not candidates:
        for img in index.all_files():
            if token in img.stem:
                candidates = [img]
                break

    if not candidates:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="image_not_found",
                message=f"Imagem não encontrada para token {token}",
            )
        )
        return [], issues

    chosen = sorted(candidates, key=lambda i: i.filename)[0]
    return [chosen.path_str], issues


def _infer_prefix_from_cam(cam_value: str) -> str | None:
    """Se Cam contiver prefixo alfanumérico (ex.: E116K244710F001), extrai para match."""
    cam_value = cam_value.strip()
    if not cam_value or cam_value.isdigit():
        return None
    match = re.match(r"^([A-Za-z][\w]*?)(\d{3,6})$", cam_value)
    if match:
        prefix = match.group(1)
        return prefix if any(c.isalpha() for c in prefix) else None
    return None


def attach_images_to_anomalies(
    anomalies: list[Anomaly],
    images_dir: Path,
) -> tuple[list[Anomaly], list[ValidationIssue]]:
    """Mapeia uma imagem por anomalia com base em nr_foto ou Cam inicial."""
    index: ImageIndex = build_image_index(images_dir)
    all_issues: list[ValidationIssue] = []
    updated: list[Anomaly] = []

    for anomaly in anomalies:
        token = anomaly.resolved_photo_token
        prefix_hint = _infer_prefix_from_cam(token) or _infer_prefix_from_cam(
            anomaly.image_range_start
        )
        paths, issues = resolve_image_for_token(index, token, prefix_hint=prefix_hint)
        all_issues.extend(issues)
        updated.append(anomaly.model_copy(update={"images": paths}))

    mapped = sum(len(a.images) for a in updated)
    logger.info("Mapeamento de imagens: %d arquivo(s) vinculado(s)", mapped)
    return updated, all_issues
