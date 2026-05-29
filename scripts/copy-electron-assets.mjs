import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dist = path.join(root, 'electron', 'dist')

for (const name of ['splash.html', 'error.html']) {
  fs.copyFileSync(path.join(root, 'electron', name), path.join(dist, name))
}

console.log('Electron assets copiados para electron/dist/')
