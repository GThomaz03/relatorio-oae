import type {
  AnalysisResult,
  ProcessingLogEntry,
  ProcessingState,
  ProcessingStep,
  Project,
} from '@/types/project'
import {
  analyzeProject,
  ApiError,
  buildPhotoLayoutPayload,
  generateProjectReport,
  resolveMediaUrl,
  uploadCustomTemplate,
  uploadProjectFiles,
} from '@/services/api-client'
import { useFileStagingStore } from '@/store/file-staging-store'
import { useProjectStore } from '@/store/project-store'
import { useTemplateStore } from '@/store/template-store'

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const INITIAL_STEPS: ProcessingStep[] = [
  { id: 'excel', label: 'Leitura da planilha', status: 'pending' },
  { id: 'photos', label: 'Organização das fotos', status: 'pending' },
  { id: 'descriptions', label: 'Geração das descrições', status: 'pending' },
  { id: 'template', label: 'Inserção no template', status: 'pending' },
  { id: 'pagination', label: 'Paginação', status: 'pending' },
  { id: 'export', label: 'Exportação DOCX', status: 'pending' },
]

export function createInitialProcessingState(): ProcessingState {
  return {
    progress: 0,
    steps: INITIAL_STEPS.map((s) => ({ ...s })),
    logs: [],
    isComplete: false,
  }
}

export function normalizeAnalysisResult(data: AnalysisResult): AnalysisResult {
  return {
    ...data,
    anomalies: data.anomalies.map((anomaly) => ({
      ...anomaly,
      thumbnailUrl: resolveMediaUrl(anomaly.thumbnailUrl) ?? null,
      availableImages: (anomaly.availableImages ?? []).map((option) => ({
        ...option,
        thumbnailUrl: resolveMediaUrl(option.thumbnailUrl) ?? option.thumbnailUrl,
      })),
    })),
    photos: data.photos.map((photo) => ({
      ...photo,
      thumbnailUrl: resolveMediaUrl(photo.thumbnailUrl) ?? photo.thumbnailUrl,
    })),
  }
}

async function ensureUploaded(project: Project): Promise<number> {
  const staging = useFileStagingStore.getState()
  const desktop = window.electronAPI
  let imagesCount = 0

  if (desktop?.uploadProjectFiles) {
    const paths = staging.getDesktopPaths(project.id)
    if (!paths?.excelPath || !paths?.imagesDirPath) {
      throw new ApiError(
        'Arquivos não encontrados. Volte ao cadastro e selecione novamente a planilha e a pasta de fotos.',
        400,
      )
    }
    const uploadResult = await desktop.uploadProjectFiles(
      project.id,
      paths.excelPath,
      paths.imagesDirPath,
    )
    imagesCount = uploadResult.images_count ?? 0
  } else {
    const excel = staging.getExcel(project.id)
    const images = staging.getImages(project.id)

    if (!excel || images.length === 0) {
      throw new ApiError(
        'Arquivos não encontrados na memória. Volte ao cadastro e selecione novamente a planilha e a pasta de fotos.',
        400,
      )
    }

    const uploadResult = await uploadProjectFiles(project.id, excel, images)
    imagesCount = uploadResult.images_count
  }

  if (imagesCount === 0) {
    throw new ApiError(
      'Nenhuma imagem encontrada na pasta enviada. Verifique se a pasta contém arquivos .jpg, .jpeg ou .png (inclusive em subpastas).',
      400,
    )
  }

  const templateStore = useTemplateStore.getState()
  if (templateStore.useCustomTemplate && templateStore.hasCustomBlob()) {
    const blob = templateStore.getCustomBlob()!
    await uploadCustomTemplate(project.id, blob, templateStore.getActiveTemplateName())
  }

  return imagesCount
}

export async function runAnalysis(project: Project): Promise<AnalysisResult> {
  const imagesUploaded = await ensureUploaded(project)
  console.info(
    `[OAE] Upload concluído: ${imagesUploaded} imagem(ns) indexável(is) no servidor.`,
  )
  const data = (await analyzeProject(project.id, project)) as AnalysisResult
  const normalized = normalizeAnalysisResult(data)
  if (normalized.summary.imagesFound === 0) {
    throw new ApiError(
      'A análise não encontrou imagens vinculadas às anomalias. Confira se os códigos das fotos na planilha correspondem aos nomes dos arquivos e selecione novamente a pasta de fotos.',
      400,
    )
  }
  return normalized
}

export interface ReportGenerationResult {
  reportPath: string
  reportDownloadUrl: string
  outputDownloadUrl: string
  photosDownloadUrl: string
  publishedOutputDir?: string
  publishedPhotosDir?: string
  stats: { pageCount: number; photoCount: number; anomalyCount: number }
}

export async function runReportGeneration(
  project: Project,
  analysis: AnalysisResult,
  onUpdate: (state: ProcessingState) => void,
): Promise<ReportGenerationResult> {
  let state = createInitialProcessingState()
  onUpdate(state)

  state = {
    ...state,
    steps: state.steps.map((step, index) =>
      index === 0 ? { ...step, status: 'running' } : step,
    ),
    progress: 5,
  }
  onUpdate(state)

  await ensureUploaded(project)

  useProjectStore.getState().saveProjectDraft(project.id)

  const selectedPhotos = analysis.anomalies.reduce<Record<string, string>>((acc, anomaly) => {
    if (anomaly.selectedPhotoNumber) {
      acc[anomaly.id] = anomaly.selectedPhotoNumber
    }
    return acc
  }, {})

  const desktopPaths = useFileStagingStore.getState().getDesktopPaths(project.id)
  const photoLayout = buildPhotoLayoutPayload(analysis)
  const result = await generateProjectReport(
    project.id,
    project,
    selectedPhotos,
    desktopPaths,
    photoLayout,
  )

  for (let i = 0; i < result.steps.length; i++) {
    const step = result.steps[i]!
    const stepLogs: ProcessingLogEntry[] = result.logs
      .filter((_, logIndex) => logIndex === i || (i === result.steps.length - 1 && logIndex >= i))
      .slice(0, 1)
      .map((log, logIndex) => ({
        id: `${step.id}-${logIndex}`,
        level: (log.level === 'ok' ? 'ok' : 'info') as ProcessingLogEntry['level'],
        message: log.message,
        timestamp: new Date().toISOString(),
      }))

    const steps = result.steps.map((s, idx) => ({
      id: s.id as ProcessingStep['id'],
      label: s.label,
      status: (idx < i ? 'done' : idx === i ? 'running' : 'pending') as ProcessingStep['status'],
    }))

    state = {
      ...state,
      steps,
      progress: Math.round(((i + 0.5) / result.steps.length) * 100),
      logs: [...state.logs, ...stepLogs],
    }
    onUpdate({ ...state })
    await delay(400)
  }

  const allLogs: ProcessingLogEntry[] = result.logs.map((log, index) => ({
    id: `log-${index}`,
    level: (log.level === 'ok' ? 'ok' : 'info') as ProcessingLogEntry['level'],
    message: log.message,
    timestamp: new Date().toISOString(),
  }))

  state = {
    progress: 100,
    isComplete: true,
    steps: result.steps.map((s) => ({
      id: s.id as ProcessingStep['id'],
      label: s.label,
      status: 'done' as const,
    })),
    logs: allLogs,
  }
  onUpdate(state)

  return {
    reportPath: result.report_path,
    reportDownloadUrl: resolveMediaUrl(result.report_download_url) ?? result.report_download_url,
    outputDownloadUrl: resolveMediaUrl(result.output_download_url) ?? result.output_download_url,
    photosDownloadUrl: resolveMediaUrl(result.photos_download_url) ?? result.photos_download_url,
    publishedOutputDir: result.published_output_dir ?? undefined,
    publishedPhotosDir: result.published_photos_dir ?? undefined,
    stats: {
      pageCount: result.stats.pageCount,
      photoCount: result.stats.photoCount,
      anomalyCount: result.stats.anomalyCount,
    },
  }
}
