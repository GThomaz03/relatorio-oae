import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface DesktopUploadPaths {
  excelPath?: string
  imagesDirPath?: string
  outputDirPath?: string
}

interface FileStagingStore {
  desktopPathsByProject: Record<string, DesktopUploadPaths>

  setDesktopPaths: (projectId: string, paths: DesktopUploadPaths) => void
  getDesktopPaths: (projectId: string) => DesktopUploadPaths | undefined
  hasFiles: (projectId: string) => boolean
  copyFromProject: (sourceId: string, targetId: string) => void
  clearProject: (projectId: string) => void
}

export const useFileStagingStore = create<FileStagingStore>()(
  persist(
    (set, get) => ({
      desktopPathsByProject: {},

      setDesktopPaths: (projectId, paths) =>
        set((state) => ({
          desktopPathsByProject: {
            ...state.desktopPathsByProject,
            [projectId]: { ...state.desktopPathsByProject[projectId], ...paths },
          },
        })),

      getDesktopPaths: (projectId) => get().desktopPathsByProject[projectId],

      hasFiles: (projectId) => {
        const desktop = get().desktopPathsByProject[projectId]
        return Boolean(desktop?.excelPath && desktop?.imagesDirPath)
      },

      copyFromProject: (sourceId, targetId) =>
        set((state) => {
          const desktop = state.desktopPathsByProject[sourceId]
          if (!desktop) return state
          return {
            desktopPathsByProject: {
              ...state.desktopPathsByProject,
              [targetId]: { ...desktop },
            },
          }
        }),

      clearProject: (projectId) =>
        set((state) => {
          const { [projectId]: _d, ...desktopPathsByProject } = state.desktopPathsByProject
          return { desktopPathsByProject }
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
