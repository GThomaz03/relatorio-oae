import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  createInitialProcessingState,
  runAnalysis,
  runReportGeneration,
} from '@/services/analysis-service'
import type {
  AnalysisResult,
  AnomalyRow,
  PhotoEntry,
  ProcessingState,
  Project,
  ProjectFiles,
  ProjectStatus,
  Sentido,
} from '@/types/project'
import { useFileStagingStore } from '@/store/file-staging-store'
import { deriveProjectStatus } from '@/utils/project-status'
import { buildBridgeId } from '@/utils/bridge-id'

function createId(): string {
  return `proj-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function emptyFiles(): ProjectFiles {
  return {
    excel: null,
    photosDir: null,
    outputDir: null,
  }
}

function createEmptyProject(): Project {
  const now = new Date().toISOString()
  return {
    id: createId(),
    name: '',
    rodovia: '',
    km: '',
    sentido: 'Sul',
    observacoes: '',
    bridgePrefix: 'E',
    bridgeId: '',
    photoKm: '',
    files: emptyFiles(),
    status: 'nao_configurada',
    createdAt: now,
    updatedAt: now,
  }
}

function normalizeProject(project: Project): Project {
  const bridgePrefix = project.bridgePrefix ?? 'E'
  const rodovia = project.rodovia ?? ''
  return {
    ...project,
    bridgePrefix,
    bridgeId: project.bridgeId || buildBridgeId(bridgePrefix, rodovia),
    files: {
      excel: project.files?.excel ?? null,
      photosDir: project.files?.photosDir ?? null,
      outputDir: project.files?.outputDir ?? null,
      photoCount: project.files?.photoCount,
    },
  }
}

function hasAllFiles(files: ProjectFiles): boolean {
  return Boolean(files.excel && files.photosDir && files.outputDir)
}

function hasBasicInfo(project: Project): boolean {
  return Boolean(project.name.trim() && project.rodovia.trim() && project.km.trim())
}

function photoBelongsToAnomaly(photo: PhotoEntry, anomaly: AnomalyRow): boolean {
  if (photo.anomalyId) {
    return photo.anomalyId === anomaly.id
  }
  if (
    typeof photo.anomalyRowIndex === 'number' &&
    typeof anomaly.rowIndex === 'number'
  ) {
    return photo.anomalyRowIndex === anomaly.rowIndex
  }
  return false
}

/** Sincroniza legenda só na anomalia/foto editada (duplicatas mantêm textos independentes). */
function syncLegendInAnalysis(
  analysis: AnalysisResult,
  anomalyId: string,
  legend: string,
): AnalysisResult {
  return {
    ...analysis,
    anomalies: analysis.anomalies.map((a) =>
      a.id === anomalyId ? { ...a, legend } : a,
    ),
    photos: analysis.photos.map((p) =>
      p.anomalyId === anomalyId ? { ...p, legend } : p,
    ),
  }
}

function recomputeStatus(
  project: Project,
  hasAnalysis: boolean,
  forceStatus?: ProjectStatus,
): ProjectStatus {
  if (forceStatus) return forceStatus
  return deriveProjectStatus(
    hasBasicInfo(project),
    hasAllFiles(project.files),
    hasAnalysis,
    project.status,
  )
}

function cloneFileRef<T extends { name: string; path: string } | null>(ref: T): T {
  return ref ? ({ ...ref } as T) : ref
}

function duplicateProjectName(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return 'Obra (cópia)'
  return trimmed.endsWith('(cópia)') ? trimmed : `${trimmed} (cópia)`
}

interface ProjectStore {
  projects: Project[]
  activeProjectId: string | null
  analysisByProject: Record<string, AnalysisResult>
  processingByProject: Record<string, ProcessingState>
  isAnalyzing: boolean

  createProject: () => string
  duplicateProject: (sourceId: string) => string
  setActiveProject: (id: string | null) => void
  updateProject: (id: string, patch: Partial<Project>) => void
  updateProjectFiles: (id: string, files: Partial<ProjectFiles>) => void
  deleteProject: (id: string) => void

  startAnalysis: (id: string) => Promise<void>
  updateAnomaly: (projectId: string, anomalyId: string, patch: Partial<AnomalyRow>) => void
  deleteAnomaly: (projectId: string, anomalyId: string) => void
  reorderPhotos: (projectId: string, photoIds: string[]) => void
  duplicatePhotoAt: (projectId: string, photoId: string) => void
  updatePhotoLegend: (projectId: string, photoId: string, legend: string) => void

  saveProjectDraft: (id: string, options?: { photos?: PhotoEntry[] }) => void
  startReportGeneration: (id: string) => Promise<void>
  getActiveProject: () => Project | null
  getActiveAnalysis: () => AnalysisResult | null
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set, get) => ({
      projects: [],
      activeProjectId: null,
      analysisByProject: {},
      processingByProject: {},
      isAnalyzing: false,

      createProject: () => {
        const project = createEmptyProject()
        set((state) => ({
          projects: [project, ...state.projects],
          activeProjectId: project.id,
        }))
        return project.id
      },

      duplicateProject: (sourceId) => {
        const state = get()
        const source = state.projects.find((p) => p.id === sourceId)
        if (!source) {
          return get().createProject()
        }

        const now = new Date().toISOString()
        const newId = createId()
        const hasAnalysis = Boolean(state.analysisByProject[sourceId])

        const duplicated = normalizeProject({
          ...source,
          id: newId,
          name: duplicateProjectName(source.name),
          files: {
            excel: cloneFileRef(source.files.excel),
            photosDir: cloneFileRef(source.files.photosDir),
            outputDir: cloneFileRef(source.files.outputDir),
            photoCount: source.files.photoCount,
          },
          createdAt: now,
          updatedAt: now,
          reportPath: undefined,
          publishedOutputDir: undefined,
          publishedPhotosDir: undefined,
          reportDownloadUrl: undefined,
          outputDownloadUrl: undefined,
          photosDownloadUrl: undefined,
          reportGeneratedAt: undefined,
          reportStats: undefined,
          analysisDraftSavedAt: now,
          status: deriveProjectStatus(
            hasBasicInfo(source),
            hasAllFiles(source.files),
            hasAnalysis,
            'pronta_analise',
          ),
        })

        const analysisCopy = state.analysisByProject[sourceId]
          ? (structuredClone(state.analysisByProject[sourceId]) as AnalysisResult)
          : undefined

        set((s) => ({
          projects: [duplicated, ...s.projects],
          activeProjectId: newId,
          analysisByProject: analysisCopy
            ? { ...s.analysisByProject, [newId]: analysisCopy }
            : s.analysisByProject,
        }))

        useFileStagingStore.getState().copyFromProject(sourceId, newId)
        return newId
      },

      setActiveProject: (id) => set({ activeProjectId: id }),

      updateProject: (id, patch) => {
        set((state) => ({
          projects: state.projects.map((p) => {
            if (p.id !== id) return p
            const updated = {
              ...p,
              ...patch,
              updatedAt: new Date().toISOString(),
            }
            return {
              ...updated,
              status: recomputeStatus(updated, Boolean(state.analysisByProject[id])),
            }
          }),
        }))
      },

      updateProjectFiles: (id, files) => {
        set((state) => ({
          projects: state.projects.map((p) => {
            if (p.id !== id) return p
            const updated = {
              ...p,
              files: { ...p.files, ...files },
              updatedAt: new Date().toISOString(),
            }
            return {
              ...updated,
              status: recomputeStatus(updated, Boolean(state.analysisByProject[id])),
            }
          }),
        }))
      },

      deleteProject: (id) => {
        set((state) => {
          const { [id]: _a, ...analysisByProject } = state.analysisByProject
          const { [id]: _p, ...processingByProject } = state.processingByProject
          return {
            projects: state.projects.filter((p) => p.id !== id),
            activeProjectId: state.activeProjectId === id ? null : state.activeProjectId,
            analysisByProject,
            processingByProject,
          }
        })
      },

      startAnalysis: async (id) => {
        const project = get().projects.find((p) => p.id === id)
        if (!project) return

        set({ isAnalyzing: true })
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === id ? { ...p, status: 'processando' as ProjectStatus } : p,
          ),
        }))

        try {
          const result = await runAnalysis(project)
          set((state) => ({
            analysisByProject: { ...state.analysisByProject, [id]: result },
            projects: state.projects.map((p) =>
              p.id === id
                ? {
                    ...p,
                    status: 'em_validacao' as ProjectStatus,
                    reportStats: {
                      pageCount: 0,
                      photoCount: result.photos.length,
                      anomalyCount: result.summary.anomalyCount,
                    },
                    updatedAt: new Date().toISOString(),
                  }
                : p,
            ),
          }))
        } catch (error) {
          set((state) => ({
            projects: state.projects.map((p) =>
              p.id === id ? { ...p, status: 'erro' as ProjectStatus } : p,
            ),
          }))
          throw error
        } finally {
          set({ isAnalyzing: false })
        }
      },

      updateAnomaly: (projectId, anomalyId, patch) => {
        set((state) => {
          const analysis = state.analysisByProject[projectId]
          if (!analysis) return state
          if (patch.legend !== undefined) {
            return {
              analysisByProject: {
                ...state.analysisByProject,
                [projectId]: syncLegendInAnalysis(analysis, anomalyId, patch.legend),
              },
            }
          }
          return {
            analysisByProject: {
              ...state.analysisByProject,
              [projectId]: {
                ...analysis,
                anomalies: analysis.anomalies.map((a) =>
                  a.id === anomalyId ? { ...a, ...patch } : a,
                ),
              },
            },
          }
        })
      },

      deleteAnomaly: (projectId, anomalyId) => {
        set((state) => {
          const analysis = state.analysisByProject[projectId]
          if (!analysis) return state

          const target = analysis.anomalies.find((a) => a.id === anomalyId)
          if (!target) return state

          const anomalies = analysis.anomalies.filter((a) => a.id !== anomalyId)
          const photos = analysis.photos
            .filter((p) => !photoBelongsToAnomaly(p, target))
            .map((p, index) => ({ ...p, sequenceIndex: index + 1 }))

          return {
            analysisByProject: {
              ...state.analysisByProject,
              [projectId]: {
                ...analysis,
                anomalies,
                photos,
                summary: {
                  ...analysis.summary,
                  anomalyCount: Math.max(0, anomalies.length),
                },
              },
            },
          }
        })
      },

      duplicatePhotoAt: (projectId, photoId) => {
        set((state) => {
          const analysis = state.analysisByProject[projectId]
          if (!analysis) return state

          const photoIndex = analysis.photos.findIndex((p) => p.id === photoId)
          if (photoIndex < 0) return state

          const sourcePhoto = analysis.photos[photoIndex]!
          const sourceAnomaly =
            analysis.anomalies.find((a) => a.id === sourcePhoto.anomalyId) ??
            analysis.anomalies.find(
              (a) =>
                typeof sourcePhoto.anomalyRowIndex === 'number' &&
                a.rowIndex === sourcePhoto.anomalyRowIndex,
            )

          if (!sourceAnomaly) return state

          const newId = `anomaly-dup-${Date.now()}`
          const options = sourceAnomaly.availableImages ?? []
          const usedNumbers = new Set(
            analysis.anomalies
              .filter((a) => a.sourceAnomalyId === sourceAnomaly.id || a.id === sourceAnomaly.id)
              .map((a) => a.selectedPhotoNumber)
              .filter(Boolean),
          )
          const nextOption = options.find((opt) => !usedNumbers.has(opt.photoNumber))
          const selectedPhotoNumber = nextOption?.photoNumber ?? sourceAnomaly.selectedPhotoNumber

          const newAnomaly: AnomalyRow = {
            ...sourceAnomaly,
            id: newId,
            sourceAnomalyId: sourceAnomaly.sourceAnomalyId ?? sourceAnomaly.id,
            selectedPhotoNumber,
            imagePath: nextOption?.imagePath ?? sourceAnomaly.imagePath,
            thumbnailUrl: nextOption?.thumbnailUrl ?? sourceAnomaly.thumbnailUrl,
          }

          const newPhoto: PhotoEntry = {
            ...sourcePhoto,
            id: `photo-dup-${Date.now()}`,
            anomalyId: newId,
            anomalyRowIndex: sourceAnomaly.rowIndex,
            imagePath: newAnomaly.imagePath ?? sourcePhoto.imagePath,
            thumbnailUrl: newAnomaly.thumbnailUrl ?? sourcePhoto.thumbnailUrl,
            legend: sourcePhoto.legend,
          }

          const photos = [
            ...analysis.photos.slice(0, photoIndex + 1),
            newPhoto,
            ...analysis.photos.slice(photoIndex + 1),
          ].map((p, index) => ({ ...p, sequenceIndex: index + 1 }))

          return {
            analysisByProject: {
              ...state.analysisByProject,
              [projectId]: {
                ...analysis,
                anomalies: [...analysis.anomalies, newAnomaly],
                photos,
                summary: {
                  ...analysis.summary,
                  anomalyCount: analysis.summary.anomalyCount + 1,
                },
              },
            },
          }
        })
      },

      reorderPhotos: (projectId, photoIds) => {
        set((state) => {
          const analysis = state.analysisByProject[projectId]
          if (!analysis) return state
          const photoMap = new Map(analysis.photos.map((p) => [p.id, p]))
          const reordered: PhotoEntry[] = photoIds
            .map((pid, index) => {
              const photo = photoMap.get(pid)
              return photo ? { ...photo, sequenceIndex: index + 1 } : null
            })
            .filter(Boolean) as PhotoEntry[]
          return {
            analysisByProject: {
              ...state.analysisByProject,
              [projectId]: { ...analysis, photos: reordered },
            },
          }
        })
      },

      updatePhotoLegend: (projectId, photoId, legend) => {
        set((state) => {
          const analysis = state.analysisByProject[projectId]
          if (!analysis) return state
          const photo = analysis.photos.find((p) => p.id === photoId)
          if (!photo) return state

          const anomalyId =
            photo.anomalyId ??
            (typeof photo.anomalyRowIndex === 'number'
              ? analysis.anomalies.find((a) => a.rowIndex === photo.anomalyRowIndex)?.id
              : undefined)

          if (!anomalyId) {
            return {
              analysisByProject: {
                ...state.analysisByProject,
                [projectId]: {
                  ...analysis,
                  photos: analysis.photos.map((p) =>
                    p.id === photoId ? { ...p, legend } : p,
                  ),
                },
              },
            }
          }

          return {
            analysisByProject: {
              ...state.analysisByProject,
              [projectId]: syncLegendInAnalysis(analysis, anomalyId, legend),
            },
          }
        })
      },

      saveProjectDraft: (id, options) => {
        const now = new Date().toISOString()
        set((state) => {
          const analysis = state.analysisByProject[id]
          const nextAnalysis =
            analysis && options?.photos
              ? { ...analysis, photos: options.photos }
              : analysis

          return {
            ...(nextAnalysis
              ? {
                  analysisByProject: {
                    ...state.analysisByProject,
                    [id]: nextAnalysis,
                  },
                }
              : {}),
            projects: state.projects.map((p) =>
              p.id === id ? { ...p, analysisDraftSavedAt: now, updatedAt: now } : p,
            ),
          }
        })
      },

      startReportGeneration: async (id) => {
        const project = get().projects.find((p) => p.id === id)
        const analysis = get().analysisByProject[id]
        if (!project || !analysis) return

        const enrichedProject: Project = {
          ...project,
          reportStats: {
            pageCount: 0,
            photoCount: analysis.photos.length,
            anomalyCount: analysis.summary.anomalyCount,
          },
        }

        set((state) => ({
          processingByProject: {
            ...state.processingByProject,
            [id]: createInitialProcessingState(),
          },
          projects: state.projects.map((p) =>
            p.id === id ? { ...p, status: 'processando' as ProjectStatus } : p,
          ),
        }))

        try {
          const result = await runReportGeneration(enrichedProject, analysis, (processing) => {
            set((state) => ({
              processingByProject: { ...state.processingByProject, [id]: processing },
            }))
          })

          set((state) => ({
            projects: state.projects.map((p) =>
              p.id === id
                ? {
                    ...p,
                    status: 'relatorio_gerado' as ProjectStatus,
                    reportPath: result.reportPath,
                    publishedOutputDir: result.publishedOutputDir,
                    publishedPhotosDir: result.publishedPhotosDir,
                    reportDownloadUrl: result.reportDownloadUrl,
                    outputDownloadUrl: result.outputDownloadUrl,
                    photosDownloadUrl: result.photosDownloadUrl,
                    reportGeneratedAt: new Date().toISOString(),
                    reportStats: result.stats,
                    updatedAt: new Date().toISOString(),
                  }
                : p,
            ),
          }))
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Erro ao gerar relatório'
          set((state) => ({
            processingByProject: {
              ...state.processingByProject,
              [id]: {
                ...(state.processingByProject[id] ?? createInitialProcessingState()),
                error: message,
                isComplete: false,
              },
            },
            projects: state.projects.map((p) =>
              p.id === id ? { ...p, status: 'erro' as ProjectStatus } : p,
            ),
          }))
        }
      },

      getActiveProject: () => {
        const { activeProjectId, projects } = get()
        return projects.find((p) => p.id === activeProjectId) ?? null
      },

      getActiveAnalysis: () => {
        const { activeProjectId, analysisByProject } = get()
        return activeProjectId ? analysisByProject[activeProjectId] ?? null : null
      },
    }),
    {
      name: 'oae-report-projects',
      partialize: (state) => ({
        projects: state.projects,
        activeProjectId: state.activeProjectId,
        analysisByProject: state.analysisByProject,
      }),
      merge: (persisted, current) => {
        const saved = persisted as Partial<typeof current> | undefined
        if (!saved?.projects) return current
        return {
          ...current,
          ...saved,
          projects: saved.projects.map((p) => normalizeProject(p as Project)),
        }
      },
    },
  ),
)

export const SENTIDO_OPTIONS: Sentido[] = [
  'Norte',
  'Sul',
  'Leste',
  'Oeste',
  'Crescente',
  'Decrescente',
]
