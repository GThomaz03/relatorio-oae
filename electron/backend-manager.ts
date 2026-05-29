import { ChildProcess, spawn } from 'child_process'
import fs from 'fs'
import path from 'path'
import { APP_NAME, DEFAULT_PORT, getBackendBundleDir, getDataDir, isDev, readBackendPort } from './config'
import { FileLogger } from './logger'

export class BackendManager {
  private process: ChildProcess | null = null
  private logger = new FileLogger('backend.log')
  private port = DEFAULT_PORT

  getPort(): number {
    return this.port
  }

  getApiBase(): string {
    return `http://127.0.0.1:${this.port}/api`
  }

  getLogPath(): string {
    return this.logger.getPath()
  }

  async start(): Promise<number> {
    const dataDir = getDataDir()
    fs.mkdirSync(dataDir, { recursive: true })
    fs.mkdirSync(path.join(dataDir, 'logs'), { recursive: true })

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      OAE_DATA_DIR: dataDir,
      OAE_PORT: String(process.env.OAE_PORT ?? DEFAULT_PORT),
      OAE_DESKTOP: '1',
      LOG_LEVEL: process.env.LOG_LEVEL ?? 'INFO',
    }

    if (isDev()) {
      env.OAE_BUNDLE_DIR = path.join(process.cwd(), 'backend')
      this.process = spawn('python', ['-m', 'backend.api.server_desktop'], {
        cwd: process.cwd(),
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      })
    } else {
      const bundleDir = getBackendBundleDir()
      const exePath = path.join(bundleDir, 'oae-backend.exe')
      if (!fs.existsSync(exePath)) {
        throw new Error(`Backend empacotado não encontrado: ${exePath}`)
      }
      // PyInstaller resolve assets via sys._MEIPASS — não sobrescrever OAE_BUNDLE_DIR
      this.process = spawn(exePath, [], {
        cwd: bundleDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      })
    }

    this.process.stdout?.on('data', (chunk: Buffer) => {
      this.logger.info(chunk.toString().trimEnd())
    })
    this.process.stderr?.on('data', (chunk: Buffer) => {
      this.logger.error(chunk.toString().trimEnd())
    })

    this.process.on('exit', (code, signal) => {
      this.logger.warn(`Backend encerrado (code=${code}, signal=${signal})`)
      this.process = null
    })

    this.port = await readBackendPort(dataDir)
    await this.waitForHealth()
    return this.port
  }

  private async waitForHealth(timeoutMs = 60000): Promise<void> {
    const start = Date.now()
    const url = `http://127.0.0.1:${this.port}/api/health`

    while (Date.now() - start < timeoutMs) {
      try {
        const response = await fetch(url)
        if (response.ok) return
      } catch {
        // retry
      }
      await new Promise((r) => setTimeout(r, 500))
    }
    throw new Error(`Backend não respondeu em ${url} dentro de ${timeoutMs}ms`)
  }

  async stop(): Promise<void> {
    if (!this.process?.pid) return

    const pid = this.process.pid
    if (process.platform === 'win32') {
      await new Promise<void>((resolve) => {
        spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true }).on(
          'close',
          () => resolve(),
        )
      })
    } else {
      this.process.kill('SIGTERM')
    }
    this.process = null
  }

  async restart(): Promise<number> {
    await this.stop()
    return this.start()
  }
}

export function getAppTitle(): string {
  return APP_NAME
}
