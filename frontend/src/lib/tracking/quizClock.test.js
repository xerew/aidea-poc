import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createQuizClock } from './quizClock.js'

test('the first question is timed from when the quiz came into view, not from page load', () => {
  const clock = createQuizClock()
  clock.show(0)            // page loads; the quiz is further down
  clock.visible(100000)    // learner scrolls to it after reading 100 s of text
  assert.equal(clock.seconds(112000), 12)
})

test('later questions are timed from when they appeared', () => {
  const clock = createQuizClock()
  clock.show(0)
  clock.visible(5000)
  clock.show(20000)        // question 2
  assert.equal(clock.seconds(27500), 7.5)
})

test('coming back into view does not restart the clock', () => {
  const clock = createQuizClock()
  clock.show(0)
  clock.visible(1000)
  clock.visible(9000)
  assert.equal(clock.seconds(11000), 10)
})

test('an answer before any visibility report falls back to when the question appeared', () => {
  const clock = createQuizClock()
  clock.show(2000)
  assert.equal(clock.seconds(5000), 3)
})
