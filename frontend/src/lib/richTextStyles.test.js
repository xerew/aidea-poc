import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  CELL_BACKGROUNDS, HIGHLIGHTS, TEXT_COLORS,
  cleanPastedStyle, filterClass, filterStyle, nearestColor, tinymceFormats,
} from './richTextStyles.js'

// WCAG 2 contrast ratio between two #rrggbb colours.
function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

test('text colours are readable on white and highlights keep black text readable', () => {
  for (const c of TEXT_COLORS) assert.ok(contrast(c.hex, '#ffffff') >= 4.5, c.name)
  for (const c of [...HIGHLIGHTS, ...CELL_BACKGROUNDS]) assert.ok(contrast('#000000', c.hex) >= 4.5, c.name)
})

test('filterStyle keeps exactly the allowed declarations per tag', () => {
  assert.equal(filterStyle('color: #B91C1C; font-size: 1.25em; font-family: "Open Sans", sans-serif', 'span'),
    "color: #b91c1c; font-size: 1.25em; font-family: 'Open Sans', sans-serif")
  assert.equal(filterStyle('text-align: justify; line-height: 1.5; margin-top: 1em; padding-left: 4em', 'p'),
    'text-align: justify; line-height: 1.5; margin-top: 1em; padding-left: 4em')
  assert.equal(filterStyle('vertical-align: middle; background-color: #f1f5f9; width: 33.33%', 'td'),
    'vertical-align: middle; background-color: #f1f5f9; width: 33.33%')
  assert.equal(filterStyle('width: 100%; border-collapse: collapse; border-width: 1px', 'table'),
    'width: 100%; border-collapse: collapse')
})

test('filterStyle drops everything else', () => {
  for (const [style, tag] of [
    ['color: #ff0000', 'span'], ['position: fixed; top: 0', 'p'], ['background-image: url(https://x/y.png)', 'td'],
    ['width: expression(alert(1))', 'td'], ['behavior: url(x.htc)', 'span'], ['display: none', 'p'],
    ['font-size: 200px', 'span'], ['font-family: Comic Sans MS', 'span'], ['padding-left: 40em', 'p'],
    ['width: 120%', 'col'], ['color: #b91c1c', 'p'], ['text-align: left', 'span'], ['color: #b91c1c', 'div'],
  ]) assert.equal(filterStyle(style, tag), '', `${tag} ${style}`)
})

test('table classes only on tables, only the presets', () => {
  assert.equal(filterClass('rt-striped evil rt-pad-roomy', 'table'), 'rt-striped rt-pad-roomy')
  assert.equal(filterClass('rt-striped', 'p'), '')
})

test('nearestColor snaps to the palette', () => {
  assert.equal(nearestColor('#000000', TEXT_COLORS), '#111827')
  assert.equal(nearestColor('#b91c1d', TEXT_COLORS), '#b91c1c')
  assert.equal(nearestColor('rgb(29, 78, 216)', TEXT_COLORS), '#1d4ed8')
  assert.equal(nearestColor('#ffff00', HIGHLIGHTS), '#fef08a')
  assert.equal(nearestColor('transparent', TEXT_COLORS), null)
})

test('pasted styles are snapped, mapped or dropped', () => {
  assert.equal(cleanPastedStyle('color: rgb(0, 0, 0); font-family: Roboto, Arial; font-size: 11pt', 'span'),
    'font-family: Roboto, sans-serif')
  assert.equal(cleanPastedStyle('font-family: Calibri, sans-serif; background-color: #ffff00', 'span'),
    'background-color: #fef08a')
  assert.equal(cleanPastedStyle('background-color: #eeeeee', 'td'), 'background-color: #f1f5f9')
})

test('pasted default black text and white backgrounds mean "no colour", not a palette colour', () => {
  for (const style of ['color: #000000', 'color: rgb(34, 34, 34)', 'color: #ffffff']) {
    assert.equal(cleanPastedStyle(style, 'span'), '', style)
  }
  for (const [style, tag] of [['background-color: #ffffff', 'span'], ['background-color: rgb(255, 255, 255)', 'td'],
    ['background-color: #fdfdfd', 'th']]) assert.equal(cleanPastedStyle(style, tag), '', `${tag} ${style}`)
  assert.equal(cleanPastedStyle('color: #ff0000', 'span'), 'color: #b91c1c')
  assert.equal(cleanPastedStyle('background-color: #ffff00', 'span'), 'background-color: #fef08a')
})

test('the colour buttons start on palette colours', () => {
  const f = tinymceFormats()
  assert.equal(f.color_default_foreground, '#111827')
  assert.equal(f.color_default_background, '#fef08a')
})

test('TinyMCE formats come from the same constants', () => {
  const f = tinymceFormats()
  assert.ok(f.font_size_formats.includes('Extra-large=1.5em'))
  assert.ok(f.font_family_formats.startsWith("Lexend=Lexend, 'Noto Sans', system-ui, sans-serif;"))
  assert.equal(f.line_height_formats, '1 1.15 1.5 2')
  assert.equal(f.custom_colors, false)
  assert.deepEqual(f.color_map_foreground.slice(0, 2), ['111827', 'Dark'])
  assert.equal(f.table_background_color_map.length, 5)
})
