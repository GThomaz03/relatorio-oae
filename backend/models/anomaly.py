"""Modelo de anomalia de inspeção."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.models.anomaly_semantics import AnomalySemantics
from backend.models.structure import parse_local_code


class Anomaly(BaseModel):
    """Uma linha de anomalia normalizada a partir da planilha Excel."""

    local: str
    number: str | None = None
    face: str
    span: str | None = None
    view: str | None = None

    anomaly_type: str
    semantics: AnomalySemantics | None = Field(
        default=None,
        description="Classificação semântica (base + modificadores) derivada do texto da planilha",
    )
    crack_width: str | None = None

    quantity: float | None = None
    length: float | None = None
    width: float | None = None
    area: float | None = None

    photo_count_expected: int | None = None
    availability: str | None = None
    observations: str | None = None

    image_range_start: str
    image_range_end: str
    nr_foto: str | None = None
    images: list[str] = Field(default_factory=list)

    row_index: int | None = Field(
        default=None,
        description="Índice da linha na planilha (1-based, excluindo cabeçalho)",
    )
    client_id: str | None = Field(
        default=None,
        description="Identificador estável no frontend (ex.: anomaly-3, anomaly-dup-…)",
    )
    description_override: str | None = Field(
        default=None,
        description="Legenda editada pelo utilizador (layout/validação); unifica texto no relatório de anomalias e fotográfico",
    )
    source_anomaly_client_id: str | None = Field(
        default=None,
        description="ID da anomalia original quando esta linha é duplicata do frontend (ex.: anomaly-12)",
    )

    @property
    def structural_code(self) -> str | None:
        return parse_local_code(self.local)

    @property
    def formatted_anomaly_label(self) -> str:
        if self.semantics:
            return self.semantics.formatted_label
        return self.anomaly_type

    @property
    def template_key(self) -> str | None:
        if self.semantics:
            return self.semantics.template_key
        return None

    @property
    def image_range_raw(self) -> tuple[str, str]:
        return (self.image_range_start, self.image_range_end)

    @property
    def resolved_photo_token(self) -> str:
        """Token da foto a utilizar: nr_foto (prioridade) ou Cam inicial."""
        if self.nr_foto:
            return self.nr_foto
        return self.image_range_start

    @field_validator(
        "local",
        "number",
        "face",
        "anomaly_type",
        "image_range_start",
        "image_range_end",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if value is None:
            return value
        return str(value).strip()

    model_config = {"str_strip_whitespace": True}
