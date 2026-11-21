// "Open in Matomo" on the admin activity page: Matomo's Visits Log filtered to
// one user (Matomo gets the internal user number, see setAnalyticsUser).
// null when Matomo isn't configured, so the page hides the link.
export function matomoVisitorLogUrl(env, userId) {
  const url = (env?.VITE_MATOMO_URL || '').trim()
  const site = String(env?.VITE_MATOMO_SITE_ID ?? '').trim()
  if (!url || !site) return null
  const base = url.endsWith('/') ? url : `${url}/`
  const segment = encodeURIComponent(`userId==${userId}`)
  return `${base}index.php?module=CoreHome&action=index&idSite=${site}&period=year&date=today`
    + `#?idSite=${site}&period=year&date=today&category=General_Visitors&subcategory=Live_VisitorLog`
    + `&segment=${segment}`
}
