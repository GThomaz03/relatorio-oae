"""Modelos de domínio da inspeção OAE."""

from backend.models.anomaly import Anomaly
from backend.models.image import ImageFile
from backend.models.inspection import (
    AnomalyGroup,
    InspectionReport,
    PhotoEntry,
    PhotoReport,
    PhotoSection,
    ReportMetadata,
)
from backend.models.structure import format_local_with_number, parse_local_code

__all__ = [
    "Anomaly",
    "AnomalyGroup",
    "ImageFile",
    "InspectionReport",
    "PhotoEntry",
    "PhotoReport",
    "PhotoSection",
    "ReportMetadata",
    "format_local_with_number",
    "parse_local_code",
]
