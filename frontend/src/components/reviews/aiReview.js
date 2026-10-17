// Small display helpers for AI review data (reviews page, editor, learner box).

export const verdictTone = (verdict) => (
  verdict === 'approve' ? 'ok' : verdict === 'changes_requested' ? 'bad' : 'unsure'
)

const ICONS = { met: 'check', partly_met: 'half', not_met: 'cross' }
export const statusIcon = (status) => ICONS[status] ?? 'question'

export const percent = (x) => (x == null ? '—' : `${Math.round(x * 100)}%`)

export const kappaText = (k) => (k == null ? '—' : k.toFixed(2))

const HUMAN = { approve: 'approve', request_changes: 'changes_requested' }
export const disagrees = (aiVerdict, action) => (
  ['approve', 'changes_requested'].includes(aiVerdict) && HUMAN[action] !== aiVerdict
)
