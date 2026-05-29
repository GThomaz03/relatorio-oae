"""Agregados de relatório de inspeção."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.anomaly import Anomaly


class ReportMetadata(BaseModel):
    excel_path: Path
    images_dir: Path
    template_path: Path
    generated_at: datetime = Field(default_factory=datetime.now)
    bridge_id: str | None = None
    title: str = "Relatório de Inspeção OAE"
    bridge_location_line: str = "Ponte — BR —  — Km —"
    photo_km: str | None = None
    photo_direction: str = "S"
    photo_start: int = 1
    source_images_dir: Path | None = None
    report_photos_dir: Path | None = None

    model_config = {"arbitrary_types_allowed": True}


class AnomalyGroup(BaseModel):
    """Grupo de anomalias similares para descrição consolidada."""

    group_id: str
    section_id: str
    anomaly_type: str
    face: str | None
    view: str | None
    structural_prefix: str | None
    members: list[Anomaly]
    locals: list[str] = Field(default_factory=list)
    description: str = ""


class PhotoEntry(BaseModel):
    image_path: str
    code: str
    location_line: str
    description_line: str
    caption: str
    anomaly_number: str | None = None
    anomaly_local: str
    anomaly_row_index: int | None = None
    sequence_index: int
    figure_number: int | None = None


class PhotoSection(BaseModel):
    section_id: str
    title: str
    entries: list[PhotoEntry] = Field(default_factory=list)


class PhotoReport(BaseModel):
    sections: list[PhotoSection] = Field(default_factory=list)
    ordered_entries: list[PhotoEntry] = Field(default_factory=list)
    total_photos: int = 0


class InspectionReport(BaseModel):
    metadata: ReportMetadata
    anomalies: list[Anomaly] = Field(default_factory=list)
    groups: list[AnomalyGroup] = Field(default_factory=list)
    photo_report: PhotoReport | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def total_images_mapped(self) -> int:
        return sum(len(a.images) for a in self.anomalies)
