import { ApiError, type ManagementSettingsResponse } from '@/services/api-client'

const API_BASE = window.electronAPI.apiBase

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string }
    return data.detail ?? response.statusText
  } catch {
    return response.statusText
  }
}

export interface InputSchemaResponse {
  required_columns: Array<{
    name: string
    required: boolean
    aliases: string[]
    example: string
  }>
  optional_columns: Array<{
    name: string
    required: boolean
    aliases: string[]
    example: string
  }>
  default_sheet_names: string[]
  reference_fields: Array<{ token: string; label: string }>
}

export interface ExcelValidateResponse {
  ok: boolean
  sheet_name?: string | null
  sheet_names: string[]
  found_columns: string[]
  missing_columns: string[]
  extra_columns: string[]
  row_count: number
  preview_rows: Array<Record<string, string>>
  issues: Array<{ severity?: string; message?: string }>
  parse_warnings: number
}

export interface CatalogBaseEntry {
  key: string
  label: string
  template_key: string
  aliases: string[]
}

export interface CatalogModifierEntry {
  key: string
  label: string
  aliases: string[]
}

export interface AnomalyCatalogResponse {
  bases: CatalogBaseEntry[]
  modifiers: CatalogModifierEntry[]
  template_keys: string[]
}

export interface CatalogPreviewResponse {
  base_key: string
  base_label: string
  template_key: string
  modifier_keys: string[]
  modifier_labels: string[]
  formatted_label: string
  rendered_description: string | null
}

export interface LegendaEntry {
  code: string
  label: string
}

export interface ManagementSummaryResponse {
  checklist: Array<{ id: string; label: string; ok: boolean; hint: string }>
  description_rule_count: number
  catalog_base_count: number
  legenda_count: number
}

export interface PhotoSectionItem {
  key: string
  label: string
  order: number
}

export interface ManagementExportBundle {
  runtime_settings: Record<string, string>
  description_rules: Array<{ key: string; template: string }>
  anomaly_catalog: { bases: CatalogBaseEntry[]; modifiers: CatalogModifierEntry[] }
  legenda: { entries: LegendaEntry[] }
  exported_at: string
}

export async function getInputSchema(): Promise<InputSchemaResponse> {
  const response = await fetch(`${API_BASE}/management/input-schema`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function validateExcelFile(file: File): Promise<ExcelValidateResponse> {
  const form = new FormData()
  form.append('file', file, file.name)
  const response = await fetch(`${API_BASE}/management/validate-excel`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function getAnomalyCatalog(): Promise<AnomalyCatalogResponse> {
  const response = await fetch(`${API_BASE}/management/anomaly-catalog`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function updateAnomalyCatalog(payload: {
  bases: CatalogBaseEntry[]
  modifiers: CatalogModifierEntry[]
}): Promise<AnomalyCatalogResponse> {
  const response = await fetch(`${API_BASE}/management/anomaly-catalog`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function previewAnomalyCatalog(anomalyText: string): Promise<CatalogPreviewResponse> {
  const response = await fetch(`${API_BASE}/management/anomaly-catalog/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anomaly_text: anomalyText }),
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function getLegenda(): Promise<{ entries: LegendaEntry[] }> {
  const response = await fetch(`${API_BASE}/management/legenda`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function updateLegenda(entries: LegendaEntry[]): Promise<{ entries: LegendaEntry[] }> {
  const response = await fetch(`${API_BASE}/management/legenda`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entries }),
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function previewDescription(
  template: string,
  sampleRow?: Record<string, string>,
): Promise<{ rendered: string }> {
  const response = await fetch(`${API_BASE}/management/preview-description`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template, sample_row: sampleRow }),
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function getPhotoSections(): Promise<PhotoSectionItem[]> {
  const response = await fetch(`${API_BASE}/management/photo-sections`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function getManagementSummary(): Promise<ManagementSummaryResponse> {
  const response = await fetch(`${API_BASE}/management/summary`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function exportManagementConfig(): Promise<ManagementExportBundle> {
  const response = await fetch(`${API_BASE}/management/export`)
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  return response.json()
}

export async function importManagementConfig(file: File): Promise<void> {
  const text = await file.text()
  const response = await fetch(`${API_BASE}/management/import`, {
    method: 'PUT',
    body: text,
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
}

export type { ManagementSettingsResponse }
