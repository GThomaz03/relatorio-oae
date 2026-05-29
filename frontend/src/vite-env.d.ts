/// <reference types="vite/client" />

interface ElectronFilePayload {
  name: string
  path: string
  size: number
  lastModified: number
  data: ArrayBuffer
}

interface ElectronFolderPayload {
  name: string
  path: string
  fileCount?: number
  files?: Array<ElectronFilePayload & { relativePath: string }>
}

interface ElectronAPI {
  apiBase: string
  isDesktop: true
  selectFile: (filters?: Array<{ name: string; extensions: string[] }>) => Promise<ElectronFilePayload | null>
  selectFolder: (purpose?: 'images' | 'output') => Promise<ElectronFolderPayload | null>
  uploadProjectFiles: (
    projectId: string,
    excelPath: string,
    imagesDirPath: string,
  ) => Promise<{ status: string; images_count: number }>
  saveFile: (defaultName?: string) => Promise<string | null>
  writeFile: (filePath: string, data: ArrayBuffer | Uint8Array) => Promise<boolean>
  openPath: (targetPath: string) => Promise<string>
  showNotification: (title: string, body: string) => Promise<void>
  restartBackend: () => Promise<string>
  getLogsPath: () => Promise<string>
}

interface Window {
  electronAPI: ElectronAPI
}
