// The commands the Matomo tracker starts with: no cookies (no consent banner),
// link/download tracking, and a 15 s heartbeat so time on each page (incl. the
// last page of a visit, e.g. Documentation) is measured, not guessed.
export function matomoSetupCommands(base, siteId) {
  return [
    ['disableCookies'],
    ['enableLinkTracking'],
    ['enableHeartBeatTimer', 15],
    ['setTrackerUrl', `${base}matomo.php`],
    ['setSiteId', String(siteId)],
  ]
}
