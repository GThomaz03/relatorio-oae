import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface DesktopUploadPaths {
  excelPath?: string
  imagesDirPath?: string
  outputDirPath?: string
}

interface FileStagingStore {
  excelByProject: Record<string, File>
  imagesByProject: Record<string, File[]>
  desktopPathsByProject: Record<string, DesktopUploadPaths>

  setExcel: (projectId: string, file: File) => void
  setImages: (projectId: string, files: File[]) => void
  setDesktopPaths: (projectId: string, paths: DesktopUploadPaths) => void
  getExcel: (projectId: string) => File | undefined
  getImages: (projectId: string) => File[]
  getDesktopPaths: (projectId: string) => DesktopUploadPaths | undefined
  hasFiles: (projectId: string) => boolean
  copyFromProject: (sourceId: string, targetId: string) => void
  clearProject: (projectId: string) => void
}

export const useFileStagingStore = create<FileStagingStore>()(
  persist(
    (set, get) => ({
  excelByProject: {},
  imagesByProject: {},
  desktopPathsByProject: {},

  setExcel: (projectId, file) =>
    set((state) => ({
      excelByProject: { ...state.excelByProject, [projectId]: file },
    })),

  setImages: (projectId, files) =>
    set((state) => ({
      imagesByProject: { ...state.imagesByProject, [projectId]: files },
    })),

  setDesktopPaths: (projectId, paths) =>
    set((state) => ({
      desktopPathsByProject: {
        ...state.desktopPathsByProject,
        [projectId]: { ...state.desktopPathsByProject[projectId], ...paths },
      },
    })),

  getExcel: (projectId) => get().excelByProject[projectId],

  getImages: (projectId) => get().imagesByProject[projectId] ?? [],

  getDesktopPaths: (projectId) => get().desktopPathsByProject[projectId],

  hasFiles: (projectId) => {
    const excel = get().excelByProject[projectId]
    const images = get().imagesByProject[projectId] ?? []
    const desktop = get().desktopPathsByProject[projectId]
    const hasDesktop = Boolean(desktop?.excelPath && desktop?.imagesDirPath)
    return Boolean((excel && images.length > 0) || hasDesktop)
  },

  copyFromProject: (sourceId, targetId) =>
    set((state) => {
      const desktop = state.desktopPathsByProject[sourceId]
      const excel = state.excelByProject[sourceId]
      const images = state.imagesByProject[sourceId]
      return {
        desktopPathsByProject: desktop
          ? {
              ...state.desktopPathsByProject,
              [targetId]: { ...desktop },
            }
          : state.desktopPathsByProject,
        excelByProject: excel
          ? { ...state.excelByProject, [targetId]: excel }
          : state.excelByProject,
        imagesByProject:
          images && images.length > 0
            ? { ...state.imagesByProject, [targetId]: [...images] }
            : state.imagesByProject,
      }
    }),

  clearProject: (projectId) =>
    set((state) => {
      const { [projectId]: _e, ...excelByProject } = state.excelByProject
      const { [projectId]: _i, ...imagesByProject } = state.imagesByProject
      const { [projectId]: _d, ...desktopPathsByProject } = state.desktopPathsByProject
      return { excelByProject, imagesByProject, desktopPathsByProject }
    }),
    }),
    {
      name: 'oae-report-file-paths',
      partialize: (state) => ({
        desktopPathsByProject: state.desktopPathsByProject,
      }),
    },
  ),
)
