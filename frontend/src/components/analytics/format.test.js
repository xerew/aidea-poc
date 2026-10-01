import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formatClock, formatDuration, itemTime } from './format.js'

// A stand-in for i18next's t(): the key plus its values, so the test checks
// which wording is chosen and with what numbers.
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key)

test('formatDuration picks hours, minutes or seconds', () => {
  assert.equal(formatDuration(null, t), '—')
  assert.equal(formatDuration(35.4, t), 'analytics.course.dur.s {"s":35}')
  assert.equal(formatDuration(250, t), 'analytics.course.dur.ms {"m":4,"s":10}')
  assert.equal(formatDuration(3900, t), 'analytics.course.dur.hm {"h":1,"m":"05"}')
})

test('formatClock shows m:ss', () => {
  assert.equal(formatClock(75), '1:15')
  assert.equal(formatClock(5), '0:05')
})

test('itemTime: measured, not tracked (done before tracking) or never opened', () => {
  assert.equal(itemTime(30, 1, null, t), 'analytics.course.dur.s {"s":30}')
  assert.equal(itemTime(0, 0, '2026-09-01T10:00:00Z', t), 'analytics.course.notTracked')
  assert.equal(itemTime(0, 0, null, t), '—')
})
