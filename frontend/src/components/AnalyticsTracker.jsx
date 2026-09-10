import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { initAnalytics, trackPageview } from '../lib/analytics'

// Mounted inside the router. Loads the analytics tracker once, then reports a
// page view on every route change (an SPA has no full page reloads to count).
// Renders nothing and is inert unless an analytics provider is configured.
export default function AnalyticsTracker() {
  const location = useLocation()

  useEffect(() => { initAnalytics() }, [])

  useEffect(() => {
    trackPageview(window.location.origin + location.pathname + location.search)
  }, [location.pathname, location.search])

  return null
}
