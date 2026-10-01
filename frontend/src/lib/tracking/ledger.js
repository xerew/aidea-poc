// What the page has measured and the server has not yet confirmed: running
// totals per visit (one visit = one resource during one page visit) and the
// queued events. Totals, not deltas, so a resent message is harmless.

export const MAX_EVENTS_PER_MESSAGE = 200

export function createLedger({ pageKey, newKey, context }) {
  const visits = new Map()   // resourceId → visit
  const pending = new Set()  // resourceIds changed since the last ack
  let events = []

  const visitFor = (resourceId) => {
    let visit = visits.get(resourceId)
    if (!visit) {
      visit = { visit_key: newKey(), resource_id: resourceId, active: 0, visible: 0, completed: false, media: null, contextSent: false }
      visits.set(resourceId, visit)
    }
    pending.add(resourceId)
    return visit
  }

  const entryOf = (visit) => ({
    visit_key: visit.visit_key,
    resource_id: visit.resource_id,
    active_s: Math.floor(visit.active),
    visible_s: Math.floor(visit.visible),
    ...(visit.completed && { completed: true }),
    ...(visit.media && { media: visit.media }),
    ...(!visit.contextSent && { context }),
  })

  return {
    addTime(resourceId, seconds, active) {
      const visit = visitFor(resourceId)
      visit.visible += seconds
      if (active) visit.active += seconds
    },
    markCompleted(resourceId) { visitFor(resourceId).completed = true },
    setMedia(resourceId, media) { visitFor(resourceId).media = media },
    addEvent(resourceId, type, data = {}, at = new Date()) {
      const visit = visitFor(resourceId)
      events.push({ event_key: newKey(), visit_key: visit.visit_key, resource_id: resourceId, type, at: at.toISOString(), data })
    },
    isEmpty: () => pending.size === 0 && events.length === 0,
    // The message to send now; pass it to ack() once the server stored it.
    payload() {
      return {
        page_key: pageKey,
        visits: [...pending].map(id => entryOf(visits.get(id))),
        events: events.slice(0, MAX_EVENTS_PER_MESSAGE),
      }
    },
    ack(sent) {
      for (const entry of sent.visits) {
        const visit = visits.get(entry.resource_id)
        visit.contextSent = true
        const now = entryOf(visit)
        const unchanged = now.active_s === entry.active_s && now.visible_s === entry.visible_s
          && Boolean(now.completed) === Boolean(entry.completed) && now.media === entry.media
        if (unchanged) pending.delete(entry.resource_id)
      }
      const sentKeys = new Set(sent.events.map(e => e.event_key))
      events = events.filter(e => !sentKeys.has(e.event_key))
    },
  }
}
