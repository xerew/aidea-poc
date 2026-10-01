// Where each second of the activity page goes, and whether it counts as active.

export const IDLE_MS = 60000      // input older than this no longer makes the learner "active"
export const MAX_TICK_GAP_S = 5    // a longer gap between ticks means timers were frozen (sleep)

export function elapsedSeconds(prevMs, nowMs, visible) {
  if (!visible) return 0
  return Math.max(0, Math.min((nowMs - prevMs) / 1000, MAX_TICK_GAP_S))
}

// A playing video, else the resource the learner last interacted with (if
// recent and still on screen), else the resource filling most of the viewport.
export function pickTarget({ playing, lastResourceInput, visiblePx, now }) {
  if (playing.length) return playing[playing.length - 1]
  if (
    lastResourceInput
    && now - lastResourceInput.at < IDLE_MS
    && (visiblePx.get(lastResourceInput.resourceId) ?? 0) > 0
  ) {
    return lastResourceInput.resourceId
  }
  let best = null
  let bestPx = 0
  for (const [id, px] of visiblePx) {
    if (px > bestPx) { best = id; bestPx = px }
  }
  return best
}

export function isActive({ visible, lastInputAt, playing, now }) {
  return visible && (playing.length > 0 || now - lastInputAt < IDLE_MS)
}
