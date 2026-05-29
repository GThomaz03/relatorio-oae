import { contextBridge, ipcRenderer } from 'electron'

export interface ElectronFilePayload {
  name: string
  path: string
  size: number
  lastModified: number
  data: ArrayBuffer
}

export interface ElectronFolderPayload {
  name: string
  path: string
  fileCount?: number
  files?: Array<ElectronFilePayload & { relativePath: string }>
}

const apiBase = ipcRenderer.sendSync('electron:getApiBaseSync') as string

const electronAPI = {
  apiBase,
  isDesktop: true as const,
  selectFile: (filters?: Array<{ name: string; extensions: string[] }>) =>
    ipcRenderer.invoke('electron:selectFile', filters) as Promise<ElectronFilePayload | null>,
  selectFolder: (purpose?: 'images' | 'output') =>
    ipcRenderer.invoke('electron:selectFolder', purpose) as Promise<ElectronFolderPayload | null>,
  uploadProjectFiles: (projectId: string, excelPath: string, imagesDirPath: string) =>
    ipcRenderer.invoke('electron:uploadProjectFiles', {
      projectId,
      excelPath,
      imagesDirPath,
    }) as Promise<{ status: string; images_count: number }>,
  saveFile: (defaultName?: string) =>
    ipcRenderer.invoke('electron:saveFile', defaultName) as Promise<string | null>,
  writeFile: (filePath: string, data: ArrayBuffer | Uint8Array) =>
    ipcRenderer.invoke('electron:writeFile', filePath, data) as Promise<boolean>,
  openPath: (targetPath: string) => ipcRenderer.invoke('electron:openPath', targetPath) as Promise<string>,
  showNotification: (title: string, body: string) =>
    ipcRenderer.invoke('electron:showNotification', title, body),
  restartBackend: () => ipcRenderer.invoke('electron:restartBackend') as Promise<string>,
  getLogsPath: () => ipcRenderer.invoke('electron:getLogsPath') as Promise<string>,
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)
