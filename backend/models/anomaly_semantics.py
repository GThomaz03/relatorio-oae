"""Estrutura semântica normalizada de anomalias."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalySemantics(BaseModel):
    """Resultado do parser semântico de anomalias."""

    original_text: str
    normalized_text: str

    base_key: str
    base_label: str

    modifier_keys: list[str] = Field(default_factory=list)
    modifier_labels: list[str] = Field(default_factory=list)

    formatted_label: str
    template_key: str
    grouping_key: str
