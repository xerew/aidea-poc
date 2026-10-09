import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createH5PSession, durationSeconds, langText } from './h5pStatements.js'

const ROOT = 'https://aidea-hub.eu/h5p'
const stmt = (verb, { sub = null, result = null, description = null } = {}) => ({
  verb: { id: `http://adlnet.gov/expapi/verbs/${verb}` },
  object: {
    id: sub ? `${ROOT}?subContentId=${sub}` : ROOT,
    definition: description ? { description: { 'en-US': description } } : {},
  },
  ...(result && { result }),
})
const session = () => createH5PSession({ language: 'el', packageId: 4, packageVersion: 2 })

test('a question answered inside the activity is an answer, not a finish', () => {
  const { events, finished } = session().handle(stmt('answered', {
    sub: 'abc', description: '<p>Capital of <b>France</b>?</p>',
    result: { response: '2', success: true, score: { raw: 1, max: 1 }, duration: 'PT4.5S' },
  }), 0)
  assert.equal(finished, null)
  assert.deepEqual(events, [{ type: 'h5p_answer', data: {
    question: 'Capital of France ?', response: '2', correct: true, raw: 1, max: 1, seconds: 4.5, attempt: 1, sub_content_id: 'abc',
  } }])
})

test('the whole activity completed is a finished attempt; the next attempt is numbered 2', () => {
  const s = session()
  const first = s.handle(stmt('completed', { result: { score: { raw: 7, max: 10 }, success: true, duration: 'PT1M2S', completion: true } }), 0)
  assert.deepEqual(first.finished, { raw: 7, max: 10, success: true, duration_s: 62, attempt: 1, language: 'el', package_id: 4, package_version: 2 })
  assert.deepEqual(first.events.map(e => e.type), ['h5p_attempt'])
  const answer = s.handle(stmt('answered', { sub: 'q1', result: { response: '0' } }), 10000)
  assert.equal(answer.events[0].data.attempt, 2)
})

test('a single question at top level is both an answer and a finished attempt', () => {
  const { events, finished } = session().handle(stmt('answered', { description: 'Q', result: { score: { raw: 0, max: 1 }, success: false } }), 0)
  assert.deepEqual(events.map(e => e.type), ['h5p_answer', 'h5p_attempt'])
  assert.equal(finished.raw, 0)
})

test('dedupes a finish reported twice', () => {
  const s = session()
  s.handle(stmt('answered', { result: { score: { raw: 1, max: 2 } } }), 1000)
  const again = s.handle(stmt('completed', { result: { score: { raw: 1, max: 2 } } }), 1800)
  assert.equal(again.finished, null)
  assert.deepEqual(again.events, [])
})

test('other verbs and malformed statements are ignored', () => {
  const s = session()
  assert.deepEqual(s.handle(stmt('interacted', { sub: 'x' }), 0), { events: [], finished: null })
  assert.deepEqual(s.handle(null, 0), { events: [], finished: null })
  assert.deepEqual(s.handle({ verb: 'odd' }, 0), { events: [], finished: null })
  assert.deepEqual(s.handle(stmt('completed', { result: { completion: false } }), 0), { events: [], finished: null })
})

test('durationSeconds and langText', () => {
  assert.equal(durationSeconds('PT1H2M3.25S'), 3723.3)
  assert.equal(durationSeconds('nope'), null)
  assert.equal(langText({ 'de-DE': 'Hallo' }), 'Hallo')
  assert.equal(langText(null), '')
  assert.equal(langText({ 'en-US': 'x'.repeat(900) }).length, 500)
})

test('text is cut by character, never leaving half an emoji', () => {
  const lone = /[\ud800-\udbff](?![\udc00-\udfff])|(^|[^\ud800-\udbff])[\udc00-\udfff]/
  const question = langText({ 'en-US': 'x'.repeat(499) + '😀😀' })
  assert.equal(lone.test(question), false)
  const { events } = session().handle(stmt('answered', {
    sub: 'q', description: 'Q', result: { response: 'y'.repeat(499) + '😀😀' },
  }), 0)
  assert.equal(lone.test(events[0].data.response), false)
})

test('a whole-activity finish with no question text is an attempt only (no empty answer row)', () => {
  // Real Arithmetic Quiz statement: top-level "answered" with only a score.
  const { events } = session().handle(stmt('answered', {
    result: { score: { min: 0, max: 5, raw: 0, scaled: 0 }, completion: true, duration: 'PT29.24S' },
  }), 0)
  assert.deepEqual(events.map(e => e.type), ['h5p_attempt'])
})
