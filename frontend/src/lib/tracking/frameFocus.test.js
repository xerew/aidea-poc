import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PRESENTATION_FOCUS_MS, watchFrameFocus } from './frameFocus.js'

function fakeClock() {
  let now = 0
  let id = 0
  const timers = new Map()
  return {
    setTimer: (fn, ms) => { id += 1; timers.set(id, { fn, at: now + ms }); return id },
    clearTimer: (t) => { timers.delete(t) },
    advance(ms) {
      now += ms
      for (const [key, t] of [...timers].sort((a, b) => a[1].at - b[1].at)) {
        if (t.at <= now && timers.has(key)) { timers.delete(key); t.fn() }
      }
    },
  }
}

function setup() {
  const win = new EventTarget()
  const doc = { activeElement: null }
  const frame = { name: 'deck' }
  const clock = fakeClock()
  const changes = []
  const stop = watchFrameFocus(frame, (on) => changes.push(on), { win, doc, ...clock })
  return { win, doc, frame, clock, changes, stop }
}

test('focus entering the frame counts until focus returns', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [true])
  s.win.dispatchEvent(new Event('focus'))
  assert.deepEqual(s.changes, [true, false])
})

test('another iframe taking focus does not count', () => {
  const s = setup()
  s.doc.activeElement = { name: 'youtube' }
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [])
})

test('counting stops at the cap', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  s.clock.advance(PRESENTATION_FOCUS_MS - 1)
  assert.deepEqual(s.changes, [true])
  s.clock.advance(1)
  assert.deepEqual(s.changes, [true, false])
  assert.equal(PRESENTATION_FOCUS_MS, 300000)
})

test('stop clears listeners and reports not attending', () => {
  const s = setup()
  s.doc.activeElement = s.frame
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  s.stop()
  assert.deepEqual(s.changes, [true, false])
  s.win.dispatchEvent(new Event('blur'))
  s.clock.advance(0)
  assert.deepEqual(s.changes, [true, false])
})
