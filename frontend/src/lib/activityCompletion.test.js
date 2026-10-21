import { test } from 'node:test'
import assert from 'node:assert/strict'
import { activityButtonState, selfCompletes } from './activityCompletion.js'

const r = (id, type, extra = {}) => ({ id, type, is_completed: false, ...extra })

test('which resources the activity button covers', () => {
  for (const type of ['text', 'image', 'video', 'pdf', 'presentation']) assert.equal(selfCompletes(r(1, type)), true, type)
  assert.equal(selfCompletes(r(1, 'h5p', { h5p_self_complete: true })), true)
  for (const res of [r(1, 'quiz'), r(1, 'assignment'), r(1, 'h5p')]) assert.equal(selfCompletes(res), false, res.type)
})

test('button with a pending text and an unfinished quiz', () => {
  assert.deepEqual(activityButtonState([r(1, 'text'), r(2, 'quiz'), r(3, 'image', { is_completed: true })]),
    { show: true, done: false, pendingIds: [1], showNote: true })
})

test('all covered resources done: completed state, no note when the quiz is done too', () => {
  assert.deepEqual(activityButtonState([r(1, 'text', { is_completed: true }), r(2, 'quiz', { is_completed: true })]),
    { show: true, done: true, pendingIds: [], showNote: false })
})

test('no button for an activity with only a quiz or an assignment', () => {
  assert.equal(activityButtonState([r(1, 'quiz')]).show, false)
  assert.equal(activityButtonState([r(1, 'assignment')]).show, false)
  assert.equal(activityButtonState([]).show, false)
})
