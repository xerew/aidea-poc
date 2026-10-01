import { test } from 'node:test'
import assert from 'node:assert/strict'
import { MAX_EVENTS_PER_MESSAGE, createLedger } from './ledger.js'

const makeLedger = () => {
  let n = 0
  return createLedger({ pageKey: 'page', newKey: () => `k${++n}`, context: { device: 'desktop' } })
}

test('time accumulates per resource; totals are floored; context sent once', () => {
  const l = makeLedger()
  l.addTime(5, 1.6, true)
  l.addTime(5, 1.6, false)
  l.addTime(6, 2, true)
  const body = l.payload()
  assert.equal(body.page_key, 'page')
  assert.deepEqual(body.visits[0], { visit_key: 'k1', resource_id: 5, active_s: 1, visible_s: 3, context: { device: 'desktop' } })
  assert.equal(body.visits[1].resource_id, 6)
  l.ack(body)
  assert.equal(l.isEmpty(), true)
  l.addTime(5, 1, true)
  assert.deepEqual(l.payload().visits, [{ visit_key: 'k1', resource_id: 5, active_s: 2, visible_s: 4 }])
})

test('changes made while a message is in flight stay pending after ack', () => {
  const l = makeLedger()
  l.addTime(5, 2, true)
  const body = l.payload()
  l.addTime(5, 2, true)
  l.ack(body)
  assert.equal(l.isEmpty(), false)
  assert.equal(l.payload().visits[0].visible_s, 4)
})

test('events link to the visit, mark it pending and clear on ack', () => {
  const l = makeLedger()
  l.addEvent(9, 'pdf_open', {}, new Date('2026-10-01T10:00:00Z'))
  const body = l.payload()
  assert.deepEqual(body.events, [{ event_key: 'k2', visit_key: 'k1', resource_id: 9, type: 'pdf_open', at: '2026-10-01T10:00:00.000Z', data: {} }])
  assert.equal(body.visits[0].visit_key, 'k1')
  l.ack(body)
  assert.equal(l.isEmpty(), true)
})

test('completed and media ride along with the visit', () => {
  const l = makeLedger()
  l.markCompleted(5)
  l.setMedia(5, { covered_pct: 10, furthest_s: 30, duration_s: 300 })
  const [visit] = l.payload().visits
  assert.equal(visit.completed, true)
  assert.deepEqual(visit.media, { covered_pct: 10, furthest_s: 30, duration_s: 300 })
})

test('events are sent in batches of at most 200', () => {
  const l = makeLedger()
  for (let i = 0; i < 250; i++) l.addEvent(1, 'video_play', { position: i })
  const first = l.payload()
  assert.equal(first.events.length, MAX_EVENTS_PER_MESSAGE)
  l.ack(first)
  assert.equal(l.payload().events.length, 50)
})
