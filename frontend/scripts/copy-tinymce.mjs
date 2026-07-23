// Copy the self-hosted TinyMCE assets into public/tinymce so they are served
// at /tinymce (dev) and bundled into dist (build). Runs via predev/prebuild.
import { cpSync, existsSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = join(here, '..', 'node_modules', 'tinymce')
const dest = join(here, '..', 'public', 'tinymce')

if (!existsSync(src)) {
  console.error('[copy-tinymce] node_modules/tinymce not found — run npm install first.')
  process.exit(1)
}

rmSync(dest, { recursive: true, force: true })
cpSync(src, dest, { recursive: true })
console.log('[copy-tinymce] copied TinyMCE assets to public/tinymce')
