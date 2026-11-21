// /analytics/courses/:id?learner=<user id> opens that learner's timeline
// directly (linked from the admin per-user activity page).
export function learnerFromSearch(search) {
  const raw = new URLSearchParams(search || '').get('learner')
  if (!raw || !/^\d+$/.test(raw)) return null
  const id = Number(raw)
  return id > 0 ? id : null
}
