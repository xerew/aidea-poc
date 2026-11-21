import { test } from 'node:test'
import assert from 'node:assert/strict'
import { learnerFromSearch } from './learnerParam.js'

test('?learner= opens that learner\'s course timeline', () => {
  assert.equal(learnerFromSearch('?learner=7'), 7)
  assert.equal(learnerFromSearch('?tab=x&learner=12'), 12)
})

test('a missing or invalid learner opens nothing', () => {
  assert.equal(learnerFromSearch(''), null)
  assert.equal(learnerFromSearch('?learner=abc'), null)
  assert.equal(learnerFromSearch('?learner=-3'), null)
})
