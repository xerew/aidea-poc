import { test } from 'node:test'
import assert from 'node:assert/strict'
import { RICH_TEXT_VALID_ELEMENTS, SANITIZE_CONFIG, isAllowedImageSrc } from './richText.js'

test('image sources: https, uploaded media and local development only', () => {
  for (const ok of ['https://aidea-hub.eu/media/a.png', '/media/lesson_assets/a.png',
    'http://localhost:8000/media/a.png', 'http://127.0.0.1:8000/media/a.png']) {
    assert.equal(isAllowedImageSrc(ok), true, ok)
  }
  for (const bad of ['javascript:alert(1)', 'data:image/png;base64,AAAA', 'http://example.com/a.png',
    '//evil.example/a.png', '', null, undefined, ' JAVASCRIPT:alert(1)']) {
    assert.equal(isAllowedImageSrc(bad), false, String(bad))
  }
})

test('editor and sanitizer allow tables and images and nothing new besides', () => {
  for (const el of ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'img']) {
    assert.ok(RICH_TEXT_VALID_ELEMENTS.includes(el), el)
    assert.ok(SANITIZE_CONFIG.ALLOWED_TAGS.includes(el), el)
  }
  for (const attr of ['src', 'alt', 'width', 'height', 'colspan', 'rowspan', 'scope', 'href', 'target', 'rel']) {
    assert.ok(SANITIZE_CONFIG.ALLOWED_ATTR.includes(attr), attr)
  }
  assert.ok(!SANITIZE_CONFIG.ALLOWED_ATTR.includes('style'))
  assert.ok(!SANITIZE_CONFIG.ALLOWED_TAGS.includes('script'))
  assert.ok(!SANITIZE_CONFIG.ALLOWED_TAGS.includes('iframe'))
})
