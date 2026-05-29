import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  Notification,
  shell,
} from 'electron'
import fs from 'fs'
import path from 'path'
import { BackendManager, getAppTitle } from './backend-manager'
import { getFrontendDistPath, getLogsDir, isDev } from './config'
import { electronLogger, startupLogger } from './logger'

const backend = new BackendManager()
let mainWindow: BrowserWindow | null = null
let splashWindow: BrowserWindow | null = null
let apiBase = ''

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif'])

function countImagesInDir(dir: string): number {
  let count = 0
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      count += countImagesInDir(full)
      continue
    }
    if (IMAGE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      count += 1
    }
  }
  return count
}

function appendImagesToForm(form: FormData, imagesDirPath: string, folderName: string): number {
  let uploaded = 0
  const walk = (dir: string, prefix = '') => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        walk(full, prefix ? `${prefix}/${entry.name}` : entry.name)
        continue
      }
      const ext = path.extname(entry.name).toLowerCase()
      if (!IMAGE_EXTENSIONS.has(ext)) continue
      const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name
      const relPath = `${folderName}/${relativePath}`.replace(/\\/g, '/')
      const buffer = fs.readFileSync(full)
      form.append('images', new Blob([buffer]), entry.name)
      form.append('relative_paths', relPath)
      uploaded += 1
    }
  }
  walk(imagesDirPath)
  return uploaded
}

function createSplashWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 420,
    height: 280,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    show: false,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  })
  win.loadFile(path.join(__dirname, 'splash.html'))
  win.once('ready-to-show', () => win.show())
  return win
}

function createErrorWindow(message: string): BrowserWindow {
  const win = new BrowserWindow({
    width: 520,
    height: 360,
    resizable: false,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  })
  win.loadFile(path.join(__dirname, 'error.html'), {
    query: { message },
  })
  return win
}

function createMainWindow(): BrowserWindow {
  const iconPath = path.join(process.cwd(), 'desktop', 'assets', 'icon.ico')
  const win = new BrowserWindow({
    width: 1366,
    height: 768,
    minWidth: 1280,
    minHeight: 720,
    show: false,
    title: getAppTitle(),
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (isDev()) {
    void win.loadURL('http://localhost:5173')
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    void win.loadFile(getFrontendDistPath())
  }

  win.once('ready-to-show', () => {
    win.show()
    win.focus()
  })
  return win
}

function registerShortcuts(win: BrowserWindow): void {
  win.webContents.on('before-input-event', (_event, input) => {
    if (input.type !== 'keyDown') return
    if (input.key === 'F11') {
      win.setFullScreen(!win.isFullScreen())
    }
    if (isDev() && input.control && input.key.toLowerCase() === 'r') {
      win.webContents.reload()
    }
    if (input.control && input.key.toLowerCase() === 'q') {
      app.quit()
    }
  })
}

function registerIpcHandlers(): void {
  ipcMain.handle('electron:getApiBase', () => apiBase)
  ipcMain.on('electron:getApiBaseSync', (event) => {
    event.returnValue = apiBase
  })
  ipcMain.handle('electron:isDesktop', () => true)
  ipcMain.handle('electron:getLogsPath', () => getLogsDir())

  ipcMain.handle(
    'electron:selectFile',
    async (_event, filters?: Array<{ name: string; extensions: string[] }>) => {
      const result = await dialog.showOpenDialog({
        properties: ['openFile'],
        filters: filters ?? [{ name: 'Todos', extensions: ['*'] }],
      })
      if (result.canceled || !result.filePaths[0]) return null
      const filePath = result.filePaths[0]
      const data = fs.readFileSync(filePath)
      const stat = fs.statSync(filePath)
      return {
        name: path.basename(filePath),
        path: filePath,
        size: stat.size,
        lastModified: stat.mtimeMs,
        data: data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength),
      }
    },
  )

  ipcMain.handle('electron:selectFolder', async (_event, purpose: 'images' | 'output' = 'images') => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
    })
    if (result.canceled || !result.filePaths[0]) return null
    const folderPath = result.filePaths[0]
    const folderName = path.basename(folderPath)

    if (purpose === 'output') {
      return { name: folderName, path: folderPath, fileCount: 0 }
    }

    const fileCount = countImagesInDir(folderPath)
    return { name: folderName, path: folderPath, fileCount }
  })

  ipcMain.handle(
    'electron:uploadProjectFiles',
    async (
      _event,
      payload: { projectId: string; excelPath: string; imagesDirPath: string },
    ) => {
      const { projectId, excelPath, imagesDirPath } = payload
      if (!apiBase) {
        throw new Error('API do backend indisponível')
      }

      const form = new FormData()
      const excelBuffer = fs.readFileSync(excelPath)
      form.append('excel', new Blob([excelBuffer]), path.basename(excelPath))

      const folderName = path.basename(imagesDirPath)
      const imagesCount = appendImagesToForm(form, imagesDirPath, folderName)
      if (imagesCount === 0) {
        throw new Error('Nenhuma imagem encontrada na pasta selecionada.')
      }

      const response = await fetch(`${apiBase}/projects/${projectId}/upload`, {
        method: 'POST',
        body: form,
      })

      if (!response.ok) {
        const detail = await response.text()
        throw new Error(detail || `Upload falhou (${response.status})`)
      }

      return response.json() as Promise<{ status: string; images_count: number }>
    },
  )

  ipcMain.handle('electron:saveFile', async (_event, defaultName?: string) => {
    const result = await dialog.showSaveDialog({
      defaultPath: defaultName ?? 'download',
    })
    if (result.canceled || !result.filePath) return null
    return result.filePath
  })

  ipcMain.handle(
    'electron:writeFile',
    async (_event, filePath: string, data: ArrayBuffer | Uint8Array) => {
      const bytes = data instanceof Uint8Array ? data : new Uint8Array(data)
      const buffer = Buffer.from(bytes)
      fs.mkdirSync(path.dirname(filePath), { recursive: true })
      fs.writeFileSync(filePath, buffer)
      return true
    },
  )

  ipcMain.handle('electron:openPath', async (_event, targetPath: string) => {
    return shell.openPath(targetPath)
  })

  ipcMain.handle('electron:showNotification', async (_event, title: string, body: string) => {
    if (Notification.isSupported()) {
      new Notification({ title, body }).show()
    }
  })

  ipcMain.handle('electron:restartBackend', async () => {
    const port = await backend.restart()
    apiBase = `http://127.0.0.1:${port}/api`
    return apiBase
  })
}

async function bootstrap(): Promise<void> {
  startupLogger.info('Iniciando aplicativo desktop')
  splashWindow = createSplashWindow()

  try {
    await backend.start()
    apiBase = backend.getApiBase()
    startupLogger.info(`Backend pronto em ${apiBase}`)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    electronLogger.error(`Falha ao iniciar backend: ${message}`)
    splashWindow?.close()
    splashWindow = null
    createErrorWindow(message)
    return
  }

  registerIpcHandlers()
  mainWindow = createMainWindow()
  registerShortcuts(mainWindow)

  splashWindow?.close()
  splashWindow = null
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)
  void bootstrap()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  void backend.stop()
})

process.on('uncaughtException', (error) => {
  electronLogger.error(`uncaughtException: ${error.message}`)
})

process.on('unhandledRejection', (reason) => {
  electronLogger.error(`unhandledRejection: ${String(reason)}`)
})
