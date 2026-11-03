import { test } from 'node:test'
import assert from 'node:assert/strict'
import { JSDOM } from 'jsdom'
import { createRichHtmlSanitizer } from './sanitizeRichHtml.js'

const clean = createRichHtmlSanitizer(new JSDOM('').window)

test('sanitizer strips every disallowed style and class', () => {
  const out = clean('<p style="position: fixed; text-align: center" class="x">A</p>'
    + '<span style="color: #ff0000; background-image: url(https://e/x.png)">B</span>'
    + '<table><tbody><tr><td style="width: expression(alert(1))">C</td></tr></tbody></table>'
    + '<span style="display:none">D</span><p style="font-size: 200px; behavior: url(x.htc)">E</p>')
  assert.ok(!/position|url\(|expression|display|behavior|200px|class="x"|#ff0000/i.test(out), out)
  assert.ok(out.includes('<p style="text-align: center">A</p>'), out)
  assert.ok(out.includes('<span>B</span>'), out)
  assert.ok(out.includes('<td>C</td>'), out)
  assert.ok(out.includes('<p>E</p>'), out)
})

test('allowed formatting reaches the learner unchanged', () => {
  const html = '<p style="line-height: 1.5; padding-left: 2em"><span style="color: #15803d; font-size: 1.25em">x</span></p>'
    + '<table class="rt-striped" style="width: 100%"><colgroup><col style="width: 30%"><col style="width: 70%"></colgroup>'
    + '<tbody><tr><th style="background-color: #f1f5f9">h</th><td style="vertical-align: top">c</td></tr></tbody></table>'
  const out = clean(html)
  for (const piece of ['line-height: 1.5', 'color: #15803d', 'class="rt-striped"', '<col style="width: 30%">',
    'background-color: #f1f5f9', 'vertical-align: top']) assert.ok(out.includes(piece), piece)
})

test('legacy content passes through unchanged apart from the table wrapper', () => {
  const legacy = '<p><strong>Hi</strong> <a href="https://x.org" target="_blank" rel="noopener">link</a></p>'
    + '<table><tbody><tr><td>a</td></tr></tbody></table>'
  assert.equal(clean(legacy), '<p><strong>Hi</strong> <a href="https://x.org" target="_blank" rel="noopener">link</a></p>'
    + '<div class="rich-table-scroll"><table><tbody><tr><td>a</td></tr></tbody></table></div>')
})

test('image rules still apply', () => {
  assert.ok(!clean('<img src="http://evil.example/a.png">').includes('<img'))
  assert.ok(clean('<img src="/media/a.png" alt="a">').includes('src="/media/a.png"'))
})

test('class survives only on tables and only the presets', () => {
  assert.equal(clean('<p class="rt-striped">a</p>'), '<p>a</p>')
  assert.ok(clean('<table class="rt-borderless evil"><tbody><tr><td>a</td></tr></tbody></table>')
    .includes('<table class="rt-borderless">'))
})
