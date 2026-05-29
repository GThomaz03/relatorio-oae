import fs from 'fs'
import path from 'path'
import { getLogsDir } from './config'

const MAX_LOG_BYTES = 5 * 1024 * 1024

function rotateIfNeeded(filePath: string): void {
  try {
    if (fs.existsSync(filePath) && fs.statSync(filePath).size > MAX_LOG_BYTES) {
      const backup = `${filePath}.1`
      if (fs.existsSync(backup)) fs.unlinkSync(backup)
      fs.renameSync(filePath, backup)
    }
  } catch {
    // ignore rotation errors
  }
}

export class FileLogger {
  private filePath: string

  constructor(filename: string) {
    const dir = getLogsDir()
    fs.mkdirSync(dir, { recursive: true })
    this.filePath = path.join(dir, filename)
  }

  write(level: string, message: string): void {
    rotateIfNeeded(this.filePath)
    const line = `${new Date().toISOString()} | ${level.padEnd(8)} | ${message}\n`
    fs.appendFileSync(this.filePath, line, 'utf-8')
  }

  info(message: string): void {
    this.write('INFO', message)
  }

  warn(message: string): void {
    this.write('WARN', message)
  }

  error(message: string): void {
    this.write('ERROR', message)
  }

  getPath(): string {
    return this.filePath
  }
}

export const electronLogger = new FileLogger('electron.log')
export const startupLogger = new FileLogger('startup.log')
