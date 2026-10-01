// Display helpers for the learning analytics pages.

// Seconds as "1 h 05 min", "4 min 10 s" or "35 s"; null → "—".
export function formatDuration(seconds, t) {
  if (seconds == null) return '—'
  const s = Math.round(seconds)
  if (s >= 3600) {
    return t('analytics.course.dur.hm', { h: Math.floor(s / 3600), m: String(Math.floor((s % 3600) / 60)).padStart(2, '0') })
  }
  if (s >= 60) return t('analytics.course.dur.ms', { m: Math.floor(s / 60), s: s % 60 })
  return t('analytics.course.dur.s', { s })
}

// A position in a video as m:ss.
export function formatClock(seconds) {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export function formatDate(iso, language) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(language, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Time for an item a learner has: measured, "not tracked" (done before
// tracking began) or "—" (never opened).
export function itemTime(seconds, visits, completedAt, t) {
  if (visits > 0) return formatDuration(seconds, t)
  return completedAt ? t('analytics.course.notTracked') : '—'
}
