import { test } from 'node:test'
import assert from 'node:assert/strict'
import { deviceFromUserAgent, pageContext } from './context.js'

test('device type from the user agent', () => {
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148', 5), 'mobile')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari/537.36', 5), 'mobile')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Linux; Android 13; SM-X200) Safari/537.36', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15', 5), 'tablet')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15', 0), 'desktop')
  assert.equal(deviceFromUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0', 0), 'desktop')
})

test('page context: language, local hour and offset ahead of UTC', () => {
  const ctx = pageContext('el', new Date(2026, 9, 1, 14, 30), 'Mozilla/5.0 (Windows NT 10.0)', 0)
  assert.equal(ctx.language, 'el')
  assert.equal(ctx.local_hour, 14)
  assert.equal(ctx.tz_offset_minutes, -new Date(2026, 9, 1, 14, 30).getTimezoneOffset())
  assert.equal(ctx.device, 'desktop')
})
