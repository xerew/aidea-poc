import { useEffect, useMemo, useRef } from 'react'
import { createTracker } from './tracker'

// Runs a tracker for the activity page while its resources are shown. A new
// page visit (new page_key) starts per activity; leaving sends what is left.
// Returns a stable API that forwards to the live tracker.
export function useActivityTracker(rootRef, activityId, resourceCount, language) {
  const trackerRef = useRef(null)

  useEffect(() => {
    const root = rootRef.current
    if (!root || resourceCount === 0) return undefined
    const tracker = createTracker({ root, language })
    trackerRef.current = tracker
    return () => {
      tracker.flush({ keepalive: true })
      tracker.stop()
      trackerRef.current = null
    }
  }, [rootRef, activityId, resourceCount, language])

  return useMemo(() => ({
    event: (...args) => trackerRef.current?.api.event(...args),
    completed: (...args) => trackerRef.current?.api.completed(...args),
    video: (...args) => trackerRef.current?.api.video(...args),
  }), [])
}
