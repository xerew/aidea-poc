import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'

const dir = new URL('../locales/', import.meta.url)
const locales = readdirSync(dir).filter(f => f.endsWith('.json'))
const load = (file) => JSON.parse(readFileSync(new URL(file, dir), 'utf8'))
const get = (obj, path) => path.split('.').reduce((o, k) => o?.[k], obj)

// Every feed kind the backend sends (hub/user_activity.py).
const KINDS = [
  'studied', 'video_finished', 'file_downloaded', 'h5p_attempt', 'h5p_error', 'enrolled', 'completed',
  'assignment_submitted', 'competency_changed', 'course_viewed', 'assignment_reviewed',
  'edit_course_created', 'edit_course_edited', 'edit_course_published', 'edit_course_unpublished',
  'edit_course_imported', 'edit_module_added', 'edit_module_edited', 'edit_module_deleted',
  'edit_modules_reordered', 'edit_module_imported', 'edit_lesson_added', 'edit_lesson_edited',
  'edit_lesson_deleted', 'edit_lessons_reordered', 'edit_resource_added', 'edit_presentation_uploaded',
  'pathway_published', 'pathway_unpublished', 'translation_requested', 'resource_edited',
  'resource_deleted', 'course_deleted', 'collaborator_added', 'collaborator_removed', 'ai_review_saved',
  'role_changed', 'pathways_rebuilt', 'message_sent', 'feedback_sent', 'access_requested', 'signed_in',
]

const KEYS = [
  'column', 'button', 'title', 'back', 'download', 'openMatomo', 'summary', 'courses', 'authoring', 'feed',
  'logins', 'loadMore', 'empty', 'noLogins', 'loadError', 'never',
  'filters.all', 'filters.learning', 'filters.authoring', 'filters.reviews', 'filters.account',
  'fields.role', 'fields.joined', 'fields.lastLogin', 'fields.onboarding', 'fields.competency',
  'fields.totalTime', 'fields.logins30d', 'yes', 'no', 'minutes',
  'cols.course', 'cols.pillar', 'cols.progress', 'cols.time', 'cols.status', 'cols.enrolled',
  'cols.lastActive', 'cols.role', 'cols.published', 'cols.edits', 'cols.when', 'cols.device', 'cols.browser',
  'authorRoles.author', 'authorRoles.co_editor', 'authorRoles.translator',
  'outcomes.approved', 'outcomes.changes_requested',
  'devices.desktop', 'devices.tablet', 'devices.mobile', 'devices.unknown',
  ...KINDS.map(k => `kinds.${k}`),
].map(k => `admin.activity.${k}`)

const params = (text) => new Set([...text.matchAll(/\{\{(\w+)\}\}/g)].map(m => m[1]))

test('every language has all activity-page texts', () => {
  assert.equal(locales.length, 9)
  for (const file of locales) {
    const json = load(file)
    for (const key of KEYS) {
      const value = get(json, key)
      assert.ok(typeof value === 'string' && value.trim(), `${file}: ${key} missing`)
    }
  }
})

test('feed texts use the same {{params}} in every language', () => {
  const en = load('en.json')
  for (const file of locales) {
    const json = load(file)
    for (const kind of KINDS) {
      const key = `admin.activity.kinds.${kind}`
      assert.deepEqual(params(get(json, key)), params(get(en, key)), `${file}: ${key}`)
    }
  }
})
