import { app } from 'electron'
import path from 'path'
import fs from 'fs'

export const APP_NAME = 'OAE Report Generator'
export const DEFAULT_PORT = 8765

export function isDev(): boolean {
  return !app.isPackaged
}

export function getUserDataDir(): string {
  return app.getPath('userData')
}

export function getDataDir(): string {
  if (process.env.OAE_DATA_DIR) {
    return process.env.OAE_DATA_DIR
  }
  return path.join(getUserDataDir(), 'data')
}

export function getLogsDir(): string {
  return path.join(getUserDataDir(), 'logs')
}

export function getBackendBundleDir(): string {
  if (isDev()) {
    return path.join(process.cwd(), 'resources', 'backend', 'oae-backend')
  }
  return path.join(process.resourcesPath, 'backend')
}

export function getFrontendDistPath(): string {
  if (isDev()) {
    return path.join(process.cwd(), 'frontend', 'dist', 'index.html')
  }
  return path.join(app.getAppPath(), 'frontend', 'dist', 'index.html')
}

export function readBackendPort(dataDir: string, timeoutMs = 30000): Promise<number> {
  const portFile = path.join(dataDir, 'backend.port')
  const start = Date.now()

  return new Promise((resolve, reject) => {
    const check = () => {
      if (fs.existsSync(portFile)) {
        const raw = fs.readFileSync(portFile, 'utf-8').trim()
        const port = Number.parseInt(raw, 10)
        if (!Number.isNaN(port)) {
          resolve(port)
          return
        }
      }
      if (Date.now() - start > timeoutMs) {
        reject(new Error(`Timeout aguardando ${portFile}`))
        return
      }
      setTimeout(check, 200)
    }
    check()
  })
}
