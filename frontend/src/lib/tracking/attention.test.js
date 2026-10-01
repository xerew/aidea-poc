import { test } from 'node:test'
import assert from 'node:assert/strict'
import { IDLE_MS, elapsedSeconds, isActive, pickTarget } from './attention.js'

const px = (entries) => new Map(entries)

test('a playing video wins, most recent first', () => {
  const target = pickTarget({ playing: [3, 7], lastResourceInput: { resourceId: 1, at: 0 }, visiblePx: px([[1, 500]]), now: 10 })
  assert.equal(target, 7)
})

test('recent interaction with a resource still on screen wins over size', () => {
  const visiblePx = px([[1, 50], [2, 600]])
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 1, at: 1000 }, visiblePx, now: 2000 }), 1)
})

test('stale or off-screen interaction falls back to the largest visible resource', () => {
  const visiblePx = px([[1, 0], [2, 600], [3, 200]])
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 1, at: 1000 }, visiblePx, now: 2000 }), 2)
  assert.equal(pickTarget({ playing: [], lastResourceInput: { resourceId: 3, at: 0 }, visiblePx, now: IDLE_MS + 1 }), 2)
})

test('nothing on screen means no target', () => {
  assert.equal(pickTarget({ playing: [], lastResourceInput: null, visiblePx: px([]), now: 0 }), null)
})

test('active needs a visible page and recent input or a playing video', () => {
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [], now: IDLE_MS - 1 }), true)
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [], now: IDLE_MS }), false)
  assert.equal(isActive({ visible: true, lastInputAt: 0, playing: [4], now: IDLE_MS * 5 }), true)
  assert.equal(isActive({ visible: false, lastInputAt: 0, playing: [4], now: 1 }), false)
})

test('elapsedSeconds: nothing while hidden, at most 5 s per tick', () => {
  assert.equal(elapsedSeconds(0, 1000, true), 1)
  assert.equal(elapsedSeconds(0, 1000, false), 0)
  assert.equal(elapsedSeconds(0, 3600000, true), 5)   // laptop slept
  assert.equal(elapsedSeconds(2000, 1000, true), 0)     // clock went back
})
