// Which parts of a video were actually played: [start, end] second ranges.
// Coverage = played seconds ÷ duration, each second counted once.

const MAX_STEP_S = 2 // samples further apart than this (or backwards) are a seek

export function mergeRanges(ranges) {
  const sorted = ranges
    .filter(([a, b]) => b > a)
    .map(([a, b]) => [a, b])
    .sort((x, y) => x[0] - y[0])
  const out = []
  for (const range of sorted) {
    const last = out[out.length - 1]
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1])
    else out.push(range)
  }
  return out
}

export function coveredPct(ranges, duration) {
  if (!(duration > 0)) return 0
  const played = mergeRanges(ranges)
    .reduce((sum, [a, b]) => sum + Math.max(0, Math.min(b, duration) - Math.max(a, 0)), 0)
  return Math.min(100, Math.round((played / duration) * 100))
}

// Turns a stream of playback positions into played ranges.
export function createRangeRecorder() {
  const ranges = []
  let current = null
  let furthest = 0
  return {
    sample(position) {
      if (!(position >= 0)) return
      if (current && position >= current[1] && position - current[1] <= MAX_STEP_S) {
        current[1] = position
      } else {
        current = [position, position]
        ranges.push(current)
      }
      furthest = Math.max(furthest, position)
    },
    // Pause / seek / end: the next sample starts a new range.
    cut() { current = null },
    ranges: () => mergeRanges(ranges),
    furthest: () => furthest,
  }
}
