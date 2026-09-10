// Provider-agnostic, cookieless web analytics.
//
// Supports Plausible or Matomo, chosen at build time via env vars. The whole
// module is inert unless VITE_ANALYTICS_PROVIDER is set, so nothing loads or
// phones home in dev or in an unconfigured deployment. Cookieless by design,
// which keeps it GDPR-friendly and avoids a consent banner.
//
// Env:
//   VITE_ANALYTICS_PROVIDER = 'plausible' | 'matomo'   (unset = disabled)
//   Plausible: VITE_PLAUSIBLE_DOMAIN (e.g. aidea-hub.eu)
//              VITE_PLAUSIBLE_SRC    (optional; self-hosted script URL)
//   Matomo:    VITE_MATOMO_URL       (e.g. https://analytics.aidea-hub.eu/)
//              VITE_MATOMO_SITE_ID   (e.g. 1)

const env = import.meta.env
const PROVIDER = (env.VITE_ANALYTICS_PROVIDER || '').toLowerCase()

let started = false

export function analyticsEnabled() {
  return PROVIDER === 'plausible' || PROVIDER === 'matomo'
}

function loadScript(src, attrs = {}) {
  const el = document.createElement('script')
  el.src = src
  el.defer = true
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v))
  document.head.appendChild(el)
}

function initPlausible() {
  const domain = env.VITE_PLAUSIBLE_DOMAIN
  if (!domain) return
  // Manual script: we send pageviews ourselves on each SPA route change, so the
  // built-in auto-tracker must not also fire (it would double-count).
  const src = env.VITE_PLAUSIBLE_SRC || 'https://plausible.io/js/script.manual.js'
  window.plausible = window.plausible
    || function stub() { (window.plausible.q = window.plausible.q || []).push(arguments) }
  loadScript(src, { 'data-domain': domain })
}

function initMatomo() {
  const url = env.VITE_MATOMO_URL
  const siteId = env.VITE_MATOMO_SITE_ID
  if (!url || !siteId) return
  const base = url.endsWith('/') ? url : `${url}/`
  window._paq = window._paq || []
  window._paq.push(['disableCookies'])   // cookieless → no consent banner needed
  window._paq.push(['enableLinkTracking'])
  window._paq.push(['setTrackerUrl', `${base}matomo.php`])
  window._paq.push(['setSiteId', String(siteId)])
  loadScript(`${base}matomo.js`)
}

// Load the tracker once. Safe to call repeatedly.
export function initAnalytics() {
  if (started || !analyticsEnabled()) return
  started = true
  try {
    if (PROVIDER === 'plausible') initPlausible()
    else if (PROVIDER === 'matomo') initMatomo()
  } catch { /* analytics must never break the app */ }
}

// Record a page view for the given URL (called on every SPA route change).
export function trackPageview(url) {
  if (!started) return
  try {
    if (PROVIDER === 'plausible' && typeof window.plausible === 'function') {
      window.plausible('pageview')
    } else if (PROVIDER === 'matomo' && window._paq) {
      window._paq.push(['setCustomUrl', url])
      window._paq.push(['setDocumentTitle', document.title])
      window._paq.push(['trackPageView'])
    }
  } catch { /* ignore */ }
}
