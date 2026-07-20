#!/usr/bin/env node
// Locale parity check: every non-English dictionary must have exactly the same
// set of leaf key paths as en.json — no missing keys, no extra keys.
// Usage: node scripts/check-locales.mjs   (run from frontend/)
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const LOCALES = ['en', 'el', 'fr', 'es', 'it', 'fi', 'sv', 'no', 'de']
const here = dirname(fileURLToPath(import.meta.url))
const localesDir = join(here, '..', 'src', 'locales')

function leafKeys(obj, prefix = '') {
  const out = []
  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === 'object' && !Array.isArray(v)) out.push(...leafKeys(v, `${prefix}${k}.`))
    else out.push(`${prefix}${k}`)
  }
  return out
}

function load(code) {
  return JSON.parse(readFileSync(join(localesDir, `${code}.json`), 'utf8'))
}

const enKeys = new Set(leafKeys(load('en')))
let failed = false

for (const code of LOCALES) {
  if (code === 'en') continue
  const keys = new Set(leafKeys(load(code)))
  const missing = [...enKeys].filter((k) => !keys.has(k))
  const extra = [...keys].filter((k) => !enKeys.has(k))
  if (missing.length || extra.length) {
    failed = true
    console.error(`\n${code}.json parity FAILED:`)
    if (missing.length) console.error(`  missing (${missing.length}): ${missing.slice(0, 20).join(', ')}${missing.length > 20 ? ' …' : ''}`)
    if (extra.length) console.error(`  extra (${extra.length}): ${extra.slice(0, 20).join(', ')}${extra.length > 20 ? ' …' : ''}`)
  }
}

if (failed) {
  console.error('\nLocale parity check FAILED.')
  process.exit(1)
}
console.log(`Locale parity OK — all ${LOCALES.length} dictionaries share ${enKeys.size} keys.`)
