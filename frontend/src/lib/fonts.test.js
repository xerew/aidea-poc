import { test } from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const read = (rel) => {
  const url = new URL(rel, import.meta.url)
  return existsSync(url) ? readFileSync(url, 'utf8') : ''
}

test('fonts are self-hosted and the default stack falls back to Noto Sans for Greek', () => {
  const index = read('../../index.html'); const css = read('../index.css'); const fonts = read('../styles/fonts.css')
  assert.ok(!/fonts\.(googleapis|gstatic)\.com/.test(index + css + fonts))
  assert.match(css, /--font-sans:\s*'Lexend', 'Noto Sans', system-ui, sans-serif/)
  for (const pkg of ['lexend', 'oswald', 'inter', 'open-sans', 'roboto', 'noto-sans', 'noto-serif', 'literata', 'fira-code'])
    assert.ok(fonts.includes(`@fontsource/${pkg}/`), pkg)
})

test('rich content CSS: tables fill the width and scroll inside their wrapper', () => {
  const css = read('../styles/richContent.css')
  assert.match(css, /\.rich-table-scroll\s*\{[^}]*overflow-x:\s*auto/)
  assert.match(css, /\.rich-html table\s*\{[^}]*width:\s*100%/)
  assert.ok(!/\.rich-html table\s*\{[^}]*display:\s*block/.test(css))
  for (const cls of ['.rt-striped', '.rt-borderless', '.rt-pad-compact', '.rt-pad-roomy']) assert.ok(css.includes(cls), cls)
  // Header rows saved before sectionCells (<thead><td>) still look like headers.
  assert.match(css, /\.rich-html thead td/)
})
