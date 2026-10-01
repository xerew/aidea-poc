import { test } from 'node:test'
import assert from 'node:assert/strict'
import { coveredPct, createRangeRecorder, mergeRanges } from './coverage.js'

test('mergeRanges joins overlapping and touching ranges', () => {
  assert.deepEqual(mergeRanges([[20, 60], [0, 30], [60, 70], [90, 95], [5, 5]]), [[0, 70], [90, 95]])
})

test('coveredPct counts each second once and clamps to the duration', () => {
  assert.equal(coveredPct([[0, 30], [20, 60]], 120), 50)
  assert.equal(coveredPct([[100, 200]], 120), 17)
  assert.equal(coveredPct([[0, 10]], 0), 0)
})

test('recorder extends a range while playing and cuts on jumps', () => {
  const rec = createRangeRecorder()
  ;[0, 1, 2, 3].forEach(p => rec.sample(p))
  rec.sample(50)            // jump forward: a seek
  rec.sample(51)
  rec.sample(10)            // jump back: another seek
  rec.sample(11.5)
  assert.deepEqual(rec.ranges(), [[0, 3], [10, 11.5], [50, 51]])
  assert.equal(rec.furthest(), 51)
})

test('recorder cut() starts a new range at the next sample', () => {
  const rec = createRangeRecorder()
  rec.sample(0); rec.sample(1); rec.cut(); rec.sample(1.5); rec.sample(2)
  assert.deepEqual(rec.ranges(), [[0, 1], [1.5, 2]])   // the paused gap is not "played"
})

test('recorder ignores invalid positions', () => {
  const rec = createRangeRecorder()
  rec.sample(NaN); rec.sample(-1); rec.sample(undefined)
  assert.deepEqual(rec.ranges(), [])
})
