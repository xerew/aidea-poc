import { test } from 'node:test'
import assert from 'node:assert/strict'
import { feedText } from './activityFeedText.js'

// A stand-in for i18next: returns the key and the params it was given.
const t = (key, params) => (params ? `${key}|${JSON.stringify(params)}` : key)
const i18n = { language: 'en', exists: () => true }
const parse = (text) => { const [key, json] = text.split('|'); return { key, params: JSON.parse(json || '{}') } }

test('a competency change with a course names the course', () => {
  const withCourse = parse(feedText({ kind: 'competency_changed', params: { old: 2, new: 3 },
    course: { id: 1, title: 'AI basics' } }, t, i18n))
  assert.equal(withCourse.key, 'admin.activity.kinds.competency_changed_course')
  assert.equal(withCourse.params.course, 'AI basics')
  const without = parse(feedText({ kind: 'competency_changed', params: { old: 2, new: 3 }, course: null }, t, i18n))
  assert.equal(without.key, 'admin.activity.kinds.competency_changed')
})

test('a translation request says what was translated', () => {
  const line = parse(feedText({ kind: 'translation_requested', params: { language: 'el', scope: 'module', course: 'AI basics' },
    course: { id: 1, title: 'AI basics' } }, t, i18n))
  assert.equal(line.params.scope, 'admin.activity.scopes.module')
})
