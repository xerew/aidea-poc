// The commands the Matomo tracker starts with: no cookies (no consent banner),
// link/download tracking, and a 15 s heartbeat so time on each page (incl. the
// last page of a visit, e.g. Documentation) is measured, not guessed.
// A signed-in user's number goes in before the first page view, so the first
// view after a reload is linked to them too.
export function matomoSetupCommands(base, siteId, userId = null) {
  const commands = [
    ['disableCookies'],
    ['enableLinkTracking'],
    ['enableHeartBeatTimer', 15],
    ['setTrackerUrl', `${base}matomo.php`],
    ['setSiteId', String(siteId)],
  ]
  if (userId != null) commands.push(['setUserId', String(userId)])
  return commands
}
