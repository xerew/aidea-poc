import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// TinyMCE is self-hosted: scripts/copy-tinymce.mjs (run via predev/prebuild)
// copies its assets into public/tinymce, which Vite serves at /tinymce in dev
// and copies into dist on build — so no cloud API key is needed.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})
