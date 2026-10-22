// Translation bar helpers (spec 2026-10-21 targeted re-translation).

const LABELS = {
  pending: 'statusPending', updating: 'statusUpdating', done: 'statusDone',
  reviewed: 'statusReviewed', failed: 'statusFailed',
}

export const statusLabelKey = (status) => `authoring.translate.${LABELS[status] ?? 'statusNone'}`
export const isRunning = (status) => status === 'pending' || status === 'updating'
export const isFinished = (status) => ['done', 'reviewed', 'failed'].includes(status)

export function retranslateOptions({ page, moduleId, activityId }) {
  if (page === 'course') return [{ scope: 'details' }, { scope: 'course' }]
  const options = []
  if (activityId) options.push({ scope: 'activity', activity_id: activityId })
  if (moduleId) options.push({ scope: 'module', module_id: moduleId })
  options.push({ scope: 'course' })
  return options
}

// A re-check entry inside the module already open: select it in place rather
// than navigating (a navigation reloads the editor and drops unsaved edits).
// null = the entry lives on another page.
export function inPageTarget(item, moduleId) {
  if (!moduleId || item.kind === 'course' || item.module_id !== moduleId) return null
  return { activityId: item.activity_id ?? null }
}
