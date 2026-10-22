import { test } from 'node:test'
import assert from 'node:assert/strict'
import { inPageTarget, isFinished, isRunning, retranslateOptions, statusLabelKey } from './translationUi.js'

test('status wording and running/finished states', () => {
  assert.equal(statusLabelKey('updating'), 'authoring.translate.statusUpdating')
  assert.equal(statusLabelKey('pending'), 'authoring.translate.statusPending')
  assert.equal(statusLabelKey(undefined), 'authoring.translate.statusNone')
  assert.equal(isRunning('updating'), true)
  assert.equal(isRunning('reviewed'), false)
  for (const st of ['done', 'reviewed', 'failed']) assert.equal(isFinished(st), true, st)
  assert.equal(isFinished('updating'), false)
})

test('re-translate options per page', () => {
  assert.deepEqual(retranslateOptions({ page: 'course' }), [{ scope: 'details' }, { scope: 'course' }])
  assert.deepEqual(retranslateOptions({ page: 'module', moduleId: 4, activityId: 9 }),
    [{ scope: 'activity', activity_id: 9 }, { scope: 'module', module_id: 4 }, { scope: 'course' }])
  assert.deepEqual(retranslateOptions({ page: 'module', moduleId: 4, activityId: null }),
    [{ scope: 'module', module_id: 4 }, { scope: 'course' }])
})

test('a re-check entry in the open module opens in place (no navigation, no reload)', () => {
  assert.deepEqual(inPageTarget({ kind: 'resource', module_id: 4, activity_id: 9 }, 4), { activityId: 9 })
  assert.deepEqual(inPageTarget({ kind: 'module', module_id: 4, activity_id: null }, 4), { activityId: null })
  assert.equal(inPageTarget({ kind: 'resource', module_id: 5, activity_id: 9 }, 4), null)
  assert.equal(inPageTarget({ kind: 'course', module_id: null, activity_id: null }, 4), null)
  assert.equal(inPageTarget({ kind: 'activity', module_id: 4, activity_id: 9 }, null), null)
})
