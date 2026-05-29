"""Schemas Pydantic para API de gerenciamento."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnSchemaItem(BaseModel):
    name: str
    required: bool
    aliases: list[str] = Field(default_factory=list)
    example: str = ""


class InputSchemaResponse(BaseModel):
    required_columns: list[ColumnSchemaItem]
    optional_columns: list[ColumnSchemaItem]
    default_sheet_names: list[str]
    reference_fields: list[dict[str, str]]


class ExcelValidateResponse(BaseModel):
    ok: bool
    sheet_name: str | None = None
    sheet_names: list[str] = Field(default_factory=list)
    found_columns: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)
    extra_columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    preview_rows: list[dict[str, str]] = Field(default_factory=list)
    issues: list[dict[str, object]] = Field(default_factory=list)
    parse_warnings: int = 0


class CatalogBaseEntry(BaseModel):
    key: str
    label: str
    template_key: str
    aliases: list[str] = Field(default_factory=list)


class CatalogModifierEntry(BaseModel):
    key: str
    label: str
    aliases: list[str] = Field(default_factory=list)


class AnomalyCatalogPayload(BaseModel):
    bases: list[CatalogBaseEntry]
    modifiers: list[CatalogModifierEntry]


class AnomalyCatalogResponse(AnomalyCatalogPayload):
    template_keys: list[str] = Field(default_factory=list)


class CatalogPreviewPayload(BaseModel):
    anomaly_text: str


class CatalogPreviewResponse(BaseModel):
    base_key: str
    base_label: str
    template_key: str
    modifier_keys: list[str]
    modifier_labels: list[str]
    formatted_label: str
    rendered_description: str | None = None


class LegendaEntry(BaseModel):
    code: str
    label: str


class LegendaPayload(BaseModel):
    entries: list[LegendaEntry]


class DescriptionPreviewPayload(BaseModel):
    template: str
    sample_row: dict[str, str] | None = None


class DescriptionPreviewResponse(BaseModel):
    rendered: str


class PhotoSectionItem(BaseModel):
    key: str
    label: str
    order: int


class ManagementExportPayload(BaseModel):
    runtime_settings: dict[str, str]
    description_rules: list[dict[str, str]]
    anomaly_catalog: AnomalyCatalogPayload
    legenda: LegendaPayload
    exported_at: str


class ManagementChecklistItem(BaseModel):
    id: str
    label: str
    ok: bool
    hint: str = ""


class ManagementSummaryResponse(BaseModel):
    checklist: list[ManagementChecklistItem]
    description_rule_count: int
    catalog_base_count: int
    legenda_count: int
