import { createContext, useContext, useMemo } from 'react'

const NOOP = { event() {}, completed() {}, video() {} }

// Provided by the activity page; anywhere else (e.g. authoring preview)
// tracking calls do nothing.
export const TrackingContext = createContext(NOOP)

// Tracking calls bound to one resource.
export function useResourceTracking(resourceId) {
  const api = useContext(TrackingContext)
  return useMemo(() => ({
    event: (type, data) => api.event(resourceId, type, data),
    video: (e) => api.video(resourceId, e),
  }), [api, resourceId])
}
