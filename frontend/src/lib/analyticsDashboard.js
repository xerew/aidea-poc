// Where the admin page's "Open analytics" button goes: the self-hosted Matomo
// dashboard (VITE_MATOMO_URL, set at build time). null = not configured, no button.
export function analyticsDashboardUrl(env = import.meta.env) {
  const url = (env?.VITE_MATOMO_URL || '').trim()
  if (!url) return null
  return url.endsWith('/') ? url : `${url}/`
}
