// Copy the h5p-standalone player into public/h5p/vendor so /h5p/player.html can
// load it (dev) and it is bundled into dist (build). Runs via predev/prebuild.
import { cpSync, existsSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = join(here, '..', 'node_modules', 'h5p-standalone', 'dist')
const dest = join(here, '..', 'public', 'h5p', 'vendor')

if (!existsSync(src)) {
  console.error('[copy-h5p] node_modules/h5p-standalone not found — run npm install first.')
  process.exit(1)
}

rmSync(dest, { recursive: true, force: true })
cpSync(src, dest, { recursive: true })
console.log('[copy-h5p] copied h5p-standalone to public/h5p/vendor')
