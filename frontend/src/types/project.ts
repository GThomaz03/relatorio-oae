export type ProjectStatus =
  | 'nao_configurada'
  | 'arquivos_pendentes'
  | 'pronta_analise'
  | 'em_validacao'
  | 'processando'
  | 'relatorio_gerado'
  | 'erro'

export type Sentido =
  | 'Norte'
  | 'Sul'
  | 'Leste'
  | 'Oeste'
  | 'Crescente'
  | 'Decrescente'

export interface FileRef {
  name: string
  path: string
  size?: number
  lastModified?: number
}

export interface ProjectFiles {
  excel: FileRef | null
  photosDir: FileRef | null
  outputDir: FileRef | null
  photoCount?: number
}

export interface Project {
  id: string
  name: string
  rodovia: string
  km: string
  sentido: Sentido
  observacoes: string
  /** Letra de identificação RSP (ex.: E) — prefixo do código da obra */
  bridgePrefix: string
  /** Identificador completo (ex.: E116), derivado de prefixo + número da rodovia */
  bridgeId: string
  photoKm: string
  files: ProjectFiles
  status: ProjectStatus
  createdAt: string
  updatedAt: string
  reportPath?: string
  publishedOutputDir?: string
  publishedPhotosDir?: string
  reportDownloadUrl?: string
  outputDownloadUrl?: string
  photosDownloadUrl?: string
  reportGeneratedAt?: string
  reportStats?: ReportStats
  /** Último salvamento manual do rascunho de análise (localStorage). */
  analysisDraftSavedAt?: string
}

export interface ReportStats {
  pageCount: number
  photoCount: number
  anomalyCount: number
}

export type AnomalyValidationStatus = 'ok' | 'warning' | 'error' | 'pending'

export interface AvailableImageOption {
  photoNumber: string
  imagePath: string
  thumbnailUrl: string
}

export interface AnomalyRow {
  id: string
  rowIndex?: number
  photoToken: string
  imagePath: string | null
  thumbnailUrl: string | null
  element: string
  anomalyType: string
  description: string
  legend: string
  observations: string
  face: string
  local: string
  status: AnomalyValidationStatus
  sequenceIndex: number
  rangeStart?: string
  rangeEnd?: string
  rangeLabel?: string
  selectedPhotoNumber?: string
  availableImages?: AvailableImageOption[]
  /** Quando duplicada a partir de outra linha na revisão fotográfica. */
  sourceAnomalyId?: string
}

export interface PhotoEntry {
  id: string
  anomalyId?: string
  anomalyRowIndex?: number
  code: string
  imagePath: string
  thumbnailUrl: string
  legend: string
  locationLine: string
  sequenceIndex: number
}

export interface AnalysisSummary {
  anomalyCount: number
  imagesFound: number
  imagesMissing: number
  inconsistencies: number
  structuralElements: string[]
}

export interface AnalysisResult {
  summary: AnalysisSummary
  anomalies: AnomalyRow[]
  photos: PhotoEntry[]
  completedAt: string
}

export type ProcessingStepId =
  | 'excel'
  | 'photos'
  | 'descriptions'
  | 'template'
  | 'pagination'
  | 'export'

export type ProcessingStepStatus = 'pending' | 'running' | 'done' | 'error'

export interface ProcessingStep {
  id: ProcessingStepId
  label: string
  status: ProcessingStepStatus
}

export interface ProcessingLogEntry {
  id: string
  level: 'ok' | 'info' | 'warn' | 'error'
  message: string
  timestamp: string
}

export interface ProcessingState {
  progress: number
  steps: ProcessingStep[]
  logs: ProcessingLogEntry[]
  isComplete: boolean
  error?: string
}
