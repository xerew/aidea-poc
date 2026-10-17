import { test } from 'node:test'
import assert from 'node:assert/strict'
import { disagrees, kappaText, percent, statusIcon, verdictTone } from './aiReview.js'

test('verdict tone and criterion icons', () => {
  assert.equal(verdictTone('approve'), 'ok')
  assert.equal(verdictTone('changes_requested'), 'bad')
  assert.equal(verdictTone('unsure'), 'unsure')
  assert.deepEqual(['met', 'partly_met', 'not_met', 'cannot_judge'].map(statusIcon), ['check', 'half', 'cross', 'question'])
})

test('percent and kappa', () => {
  assert.equal(percent(0.953), '95%')
  assert.equal(percent(null), '—')
  assert.equal(kappaText(0.4), '0.40')
  assert.equal(kappaText(null), '—')
})

test('a human decision disagrees only with a definite AI verdict', () => {
  assert.equal(disagrees('approve', 'request_changes'), true)
  assert.equal(disagrees('changes_requested', 'approve'), true)
  assert.equal(disagrees('approve', 'approve'), false)
  assert.equal(disagrees('unsure', 'approve'), false)
  assert.equal(disagrees(undefined, 'approve'), false)
})
