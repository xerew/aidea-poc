import { test } from 'node:test'
import assert from 'node:assert/strict'
import { JSDOM } from 'jsdom'
import { EDITOR_TOOLBAR, PARAGRAPH_FORMATS, TABLE_TOOLBAR, cleanNodeStyles } from './editorSetup.js'
import { cleanPastedStyle, filterStyle } from './richTextStyles.js'

const { document } = new JSDOM('').window
const fragment = (html) => {
  const div = document.createElement('div')
  div.innerHTML = html
  return div
}

test('toolbar offers every control the spec lists', () => {
  for (const b of ['fontfamily', 'fontsize', 'forecolor', 'backcolor', 'alignleft', 'aligncenter', 'alignright',
    'alignjustify', 'lineheight', 'paragraphspacing', 'outdent', 'indent']) assert.ok(EDITOR_TOOLBAR.includes(b), b)
  for (const b of ['tablecellbackgroundcolor', 'tablecellvalign', 'tablerowheader', 'tablecolheader',
    'tablestriped', 'tableborderless', 'tablepadding']) assert.ok(TABLE_TOOLBAR.includes(b), b)
})

test('paragraph spacing formats use the pinned steps', () => {
  const f = PARAGRAPH_FORMATS()
  assert.deepEqual(f.spaceBeforeLarge, { selector: 'p,h2,h3,li,blockquote', styles: { marginTop: '1em' } })
  assert.deepEqual(f.spaceAfterSmall.styles, { marginBottom: '0.25em' })
})

test('cleanNodeStyles applies the paste rules to a pasted fragment', () => {
  const root = fragment('<p style="text-align:center; font-family: Calibri"><span style="color: rgb(0,0,0); font-size: 11pt">x</span></p>'
    + '<table class="MsoTable rt-striped"><tbody><tr><td style="background-color:#eee">y</td></tr></tbody></table>')
  cleanNodeStyles(root, cleanPastedStyle)
  assert.equal(root.innerHTML, '<p style="text-align: center"><span>x</span></p>'
    + '<table class="rt-striped"><tbody><tr><td style="background-color: #f1f5f9">y</td></tr></tbody></table>')
})

test('cleanNodeStyles with the plain filter removes what it cannot keep', () => {
  const root = fragment('<p class="MsoNormal" style="mso-line-height: 2">a</p><span style="color: #ff0000">b</span>')
  cleanNodeStyles(root, filterStyle)
  assert.equal(root.innerHTML, '<p>a</p><span>b</span>')
})
