import { test } from 'node:test'
import assert from 'node:assert/strict'
import { matomoVisitorLogUrl } from './matomoLink.js'
import { matomoSetupCommands } from './matomoSetup.js'

const ENV = { VITE_MATOMO_URL: 'https://analytics.aidea-hub.eu', VITE_MATOMO_SITE_ID: '1' }

test('the Open in Matomo link shows that user\'s visits', () => {
  const url = matomoVisitorLogUrl(ENV, 42)
  assert.ok(url.startsWith('https://analytics.aidea-hub.eu/index.php?'), url)
  assert.ok(url.includes('idSite=1'))
  assert.ok(url.includes('segment=userId%3D%3D42'))
})

test('the Matomo link covers the last 365 days, not just the current calendar year', () => {
  const url = matomoVisitorLogUrl(ENV, 42)
  assert.ok(!url.includes('period=year'), url)
  assert.equal(url.split('period=range&date=last365').length - 1, 2, url) // in the query and the # route
})

test('no Matomo link unless both the address and the site id are set', () => {
  assert.equal(matomoVisitorLogUrl({ VITE_MATOMO_SITE_ID: '1' }, 42), null)
  assert.equal(matomoVisitorLogUrl({ VITE_MATOMO_URL: 'https://analytics.aidea-hub.eu' }, 42), null)
  assert.equal(matomoVisitorLogUrl({ VITE_MATOMO_URL: '  ', VITE_MATOMO_SITE_ID: '1' }, 42), null)
})

test('the tracker stays cookieless and measures time with a 15 s heartbeat', () => {
  assert.deepEqual(matomoSetupCommands('https://a.example/', '1'), [
    ['disableCookies'],
    ['enableLinkTracking'],
    ['enableHeartBeatTimer', 15],
    ['setTrackerUrl', 'https://a.example/matomo.php'],
    ['setSiteId', '1'],
  ])
})
