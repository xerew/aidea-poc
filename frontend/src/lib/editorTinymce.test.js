// The real TinyMCE (core + our plugins) in jsdom, with the exact editor
// configuration authors get (editorInit) — checks what the editor writes and
// what survives save, not just our helpers in isolation.
import { before, test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { JSDOM, VirtualConsole } from 'jsdom'
import { editorInit } from './editorSetup.js'

const TINYMCE = fileURLToPath(new URL('../../node_modules/tinymce/', import.meta.url))
const CHROME_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'

async function startEditor({ userAgent } = {}) {
  const dom = new JSDOM('<!doctype html><html><head></head><body><div id="ed"></div></body></html>',
    { runScripts: 'outside-only', pretendToBeVisual: true, url: 'http://localhost/', virtualConsole: new VirtualConsole() })
  const w = dom.window
  if (userAgent) Object.defineProperty(w.navigator, 'userAgent', { get: () => userAgent })
  // jsdom lacks layout; TinyMCE only needs these to exist.
  w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} })
  w.ResizeObserver = class { observe() {} disconnect() {} unobserve() {} }
  w.IntersectionObserver = class { observe() {} disconnect() {} unobserve() {} }
  const rect = () => ({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0 })
  w.Range.prototype.getClientRects = () => []
  w.Range.prototype.getBoundingClientRect = rect
  w.Element.prototype.getClientRects = () => []
  w.Text.prototype.getClientRects = () => []
  w.document.execCommand = () => false
  Object.defineProperty(w.HTMLElement.prototype, 'contentEditable', {
    configurable: true,
    get() { return this.getAttribute('contenteditable') ?? 'inherit' },
    set(v) { this.setAttribute('contenteditable', String(v)) },
  })
  Object.defineProperty(w.HTMLElement.prototype, 'isContentEditable', {
    configurable: true,
    get() {
      for (let n = this; n && n.nodeType === 1; n = n.parentNode) {
        const a = n.getAttribute('contenteditable')
        if (a === 'true' || a === '') return true
        if (a === 'false') return false
      }
      return false
    },
  })
  for (const file of ['tinymce.js', 'models/dom/model.js', 'themes/silver/theme.js', 'icons/default/icons.js',
    ...['lists', 'link', 'autolink', 'table', 'image'].map((p) => `plugins/${p}/plugin.js`)]) {
    w.eval(fs.readFileSync(TINYMCE + file, 'utf8'))
  }
  const [editor] = await w.tinymce.init({
    ...editorInit(),
    target: w.document.getElementById('ed'),
    inline: true,
    license_key: 'gpl',
    skin: false,
    content_css: false,
    toolbar: false,
    table_toolbar: '',
  })
  return editor
}

function selectFirstText(editor) {
  editor.focus()
  const walker = editor.getDoc().createTreeWalker(editor.getBody(), 4)
  const node = walker.nextNode()
  const rng = editor.dom.createRng()
  rng.setStart(node, 0)
  rng.setEnd(node, node.data.length)
  editor.selection.setRng(rng)
}

let editor
before(async () => { editor = await startEditor() })
const run = (html, action) => {
  editor.setContent(html)
  selectFirstText(editor)
  action()
  return editor.getContent().replace(/\n/g, '')
}
const TABLE = '<table><tbody><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></tbody></table>'

test('underline is saved (as <u>)', () => {
  assert.match(run('<p>hello</p>', () => editor.execCommand('Underline')), /<u>hello<\/u>/)
})

test('"Header row" makes real header cells', () => {
  assert.match(run(TABLE, () => editor.execCommand('mceTableRowType', false, { type: 'header' })), /<th[ >]/)
})

test('indent stops at the last allowed step instead of disappearing', () => {
  const out = run('<p>hello</p>', () => { for (let i = 0; i < 7; i++) editor.execCommand('Indent') })
  assert.match(out, /padding-left: 10em/)
})

test('line spacing set inside a table cell is kept', () => {
  assert.match(run(TABLE, () => editor.execCommand('LineHeight', false, '2')), /<td style="line-height: 2">a/)
})

test('a style dropped on load cannot come back while editing', () => {
  editor.setContent('<p style="position: fixed; text-align: center">x</p>')
  const p = editor.getBody().querySelector('p')
  assert.ok(!/position/.test(p.getAttribute('data-mce-style') ?? ''), p.outerHTML)
  assert.ok(!/position/.test(p.getAttribute('style') ?? ''), p.outerHTML)
})

test('pasting in Chrome keeps allowed formatting (cleaned), not nothing', async () => {
  const chrome = await startEditor({ userAgent: CHROME_UA })
  chrome.setContent('<p>x</p>')
  selectFirstText(chrome)
  chrome.execCommand('mceInsertClipboardContent', false, {
    html: '<p style="text-align: center; position: fixed"><span style="color: rgb(185, 28, 28); background-color: rgb(255, 255, 255)">pasted</span></p>',
  })
  const out = chrome.getContent()
  assert.match(out, /text-align: center/)
  assert.match(out, /color: #b91c1c/)
  assert.ok(!/position|background-color/.test(out), out)
})
