"""Modelo de arquivo de imagem de inspeção."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ImageDimensions(BaseModel):
    width_px: int
    height_px: int


class ImageFile(BaseModel):
    """Metadados de uma imagem indexada na pasta de inspeção."""

    filename: str
    path: Path
    stem: str
    suffix: str
    sequence_token: str | None = None
    prefix: str | None = None
    dimensions: ImageDimensions | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def path_str(self) -> str:
        return str(self.path)
