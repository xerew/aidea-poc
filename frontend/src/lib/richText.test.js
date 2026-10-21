import { test } from 'node:test'
import assert from 'node:assert/strict'
import { EDITOR_URL_OPTIONS, RICH_TEXT_VALID_ELEMENTS, SANITIZE_CONFIG, isAllowedImageSrc, makeImageUploader } from './richText.js'

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

test('the editor keeps uploaded images as absolute paths (never page-relative)', () => {
  assert.equal(EDITOR_URL_OPTIONS.relative_urls, false)
  assert.equal(EDITOR_URL_OPTIONS.remove_script_host, true)
})

test('image uploads return the stored URL; failures remove the image from the editor', async () => {
  const ok = makeImageUploader({ post: async () => ({ data: { url: 'https://aidea-hub.eu/media/x.png' } }) })
  const blobInfo = { blob: () => new Blob(['x']), filename: () => 'x.png' }
  assert.equal(await ok(blobInfo), 'https://aidea-hub.eu/media/x.png')
  const failing = makeImageUploader({ post: async () => { throw Object.assign(new Error('400'), { response: { data: { error: 'File too large (max 20 MB).' } } }) } })
  await assert.rejects(failing(blobInfo), (err) => err.remove === true && err.message === 'File too large (max 20 MB).')
})
