// Seconds a learner spent on the current quiz question. A question's clock
// starts when it appeared, but never before the quiz first came into view —
// otherwise question 1 would include the reading time of everything above it.

export function createQuizClock() {
  let shownAt = null
  let firstVisibleAt = null
  return {
    show(now) { shownAt = now },                                   // a question appeared
    visible(now) { if (firstVisibleAt === null) firstVisibleAt = now },
    seconds(now) {
      const start = Math.max(shownAt ?? now, firstVisibleAt ?? -Infinity)
      return Math.round((now - start) / 100) / 10
    },
  }
}
