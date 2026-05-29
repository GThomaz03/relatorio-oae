import type { Project, Sentido } from '@/types/project'
import type { DesktopUploadPaths } from '@/store/file-staging-store'

function apiBase(): string {
  const base = window.electronAPI?.apiBase
  if (!base) {
    throw new Error('API indisponível — execute o aplicativo desktop.')
  }
  return base
}

/** Converte URLs relativas (/api/...) em absolutas no Electron (file://). */
export function resolveMediaUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/api')) {
    const origin = apiBase().replace(/\/api\/?$/, '')
    return `${origin}${url}`
  }
  if (url.startsWith('/')) {
    return `${apiBase().replace(/\/api\/?$/, '')}${url}`
  }
  return `${apiBase()}/${url.replace(/^\//, '')}`
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string }
    return data.detail ?? response.statusText
  } catch {
    return response.statusText
  }
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${apiBase()}/health`)
    return response.ok
  } catch {
    return false
  }
}

export interface ProjectApiPayload {
  name: string
  rodovia: string
  km: string
  bridge_id: string
  photo_km: string
  photo_direction: string
  bridge_location_line: string
  title: string
  selected_photos?: Record<string, string>
  photo_layout?: Array<{
    anomaly_id: string
    source_anomaly_id?: string
    row_index?: number
    selected_photo?: string
    legend?: string
  }>
  output_dir?: string
}

export interface ManagementSettingsResponse {
  runtime_settings: Record<string, string>
  runtime_defaults: Record<string, string>
  description_rules: Array<{ key: string; template: string }>
  reference_fields: Array<{ token: string; label: string }>
  anomaly_options: string[]
}

export function resolveOutputDirPath(
  project: Project,
  desktopPaths?: DesktopUploadPaths,
): string | undefined {
  const candidate = desktopPaths?.outputDirPath ?? project.files.outputDir?.path
  if (!candidate) return undefined
  if (candidate.includes('/') || candidate.includes('\\')) {
    return candidate
  }
  return undefined
}

export function buildPhotoLayoutPayload(analysis: {
  photos: Array<{ id: string; anomalyId?: string; legend: string }>
  anomalies: Array<{
    id: string
    rowIndex?: number
    selectedPhotoNumber?: string
    sourceAnomalyId?: string
    legend?: string
  }>
}): ProjectApiPayload['photo_layout'] {
  const anomalyById = new Map(analysis.anomalies.map((a) => [a.id, a]))
  return analysis.photos
    .map((photo) => {
      const anomaly = photo.anomalyId ? anomalyById.get(photo.anomalyId) : undefined
      if (!anomaly) return null
      const legend = photo.legend?.trim() || anomaly.legend?.trim()
      return {
        anomaly_id: anomaly.id,
        source_anomaly_id: anomaly.sourceAnomalyId,
        row_index: anomaly.rowIndex,
        selected_photo: anomaly.selectedPhotoNumber,
        ...(legend ? { legend } : {}),
      }
    })
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
}

export function buildProjectPayload(
  project: Project,
  selectedPhotos?: Record<string, string>,
  desktopPaths?: DesktopUploadPaths,
  photoLayout?: ProjectApiPayload['photo_layout'],
): ProjectApiPayload {
  const outputDir = resolveOutputDirPath(project, desktopPaths)
  return {
    name: project.name,
    rodovia: project.rodovia,
    km: project.km,
    bridge_id: project.bridgeId,
    photo_km: project.photoKm || project.km.replace('+', ''),
    photo_direction: sentidoToPhotoDirection(project.sentido),
    bridge_location_line: buildBridgeLocationLine(project),
    title: `Relatório de Inspeção — ${project.name || project.bridgeId}`,
    selected_photos: selectedPhotos,
    ...(photoLayout?.length ? { photo_layout: photoLayout } : {}),
    ...(outputDir ? { output_dir: outputDir } : {}),
  }
}

export function sentidoToPhotoDirection(sentido: Sentido): string {
  const map: Record<Sentido, string> = {
    Norte: 'N',
    Sul: 'S',
    Leste: 'L',
    Oeste: 'O',
    Crescente: 'C',
    Decrescente: 'D',
  }
  return map[sentido] ?? 'S'
}

export function buildBridgeLocationLine(project: Project): string {
  const name = project.name.trim() || 'Ponte'
  const rodovia = project.rodovia.trim() || 'BR'
  const km = project.km.trim() || '—'
  return `${name} — ${rodovia} — — Km ${km} —`
}

export async function uploadCustomTemplate(projectId: string, template: Blob, name: string) {
  const form = new FormData()
  form.append('template', template, name)
  const response = await fetch(`${apiBase()}/projects/${projectId}/upload-template`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
}

export async function analyzeProject(projectId: string, project: Project) {
  const response = await fetch(`${apiBase()}/projects/${projectId}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildProjectPayload(project)),
  })
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
  return response.json()
}

export async function getManagementSettings(): Promise<ManagementSettingsResponse> {
  const response = await fetch(`${apiBase()}/management/settings`)
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
  return response.json()
}

export async function updateManagementSettings(payload: {
  runtime_settings: Record<string, string>
  description_rules: Array<{ key: string; template: string }>
}): Promise<ManagementSettingsResponse> {
  const response = await fetch(`${apiBase()}/management/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
  return response.json()
}

export interface GenerateReportResponse {
  report_path: string
  report_download_url: string
  output_download_url: string
  photos_download_url: string
  published_output_dir?: string | null
  published_photos_dir?: string | null
  stats: {
    pageCount: number
    photoCount: number
    anomalyCount: number
    elapsedSeconds?: number
    warnings?: number
    errors?: number
  }
  logs: Array<{ level: string; message: string }>
  steps: Array<{ id: string; label: string; status: string }>
}

export async function generateProjectReport(
  projectId: string,
  project: Project,
  selectedPhotos?: Record<string, string>,
  desktopPaths?: DesktopUploadPaths,
  photoLayout?: ProjectApiPayload['photo_layout'],
): Promise<GenerateReportResponse> {
  const response = await fetch(`${apiBase()}/projects/${projectId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildProjectPayload(project, selectedPhotos, desktopPaths, photoLayout)),
  })
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
  return response.json()
}

export function artifactUrl(projectId: string, kind: 'report' | 'output' | 'photos'): string {
  const paths = {
    report: `/artifacts/report`,
    output: `/artifacts/output.zip`,
    photos: `/artifacts/photos.zip`,
  }
  return `${apiBase()}/projects/${projectId}${paths[kind]}`
}

export async function openLocalPath(targetPath: string) {
  await window.electronAPI.openPath(targetPath)
}

export async function downloadArtifact(
  url: string,
  filename?: string,
  options?: { openAfterSave?: boolean },
) {
  const electron = window.electronAPI
  if (!electron?.saveFile || !electron?.writeFile) {
    throw new Error('Download indisponível — execute o aplicativo desktop.')
  }

  const savePath = await electron.saveFile(filename ?? 'download')
  if (!savePath) return

  const response = await fetch(url)
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status)
  }
  const buffer = await response.arrayBuffer()
  await electron.writeFile(savePath, buffer)
  if (options?.openAfterSave !== false) {
    await electron.openPath(savePath)
  }
}
