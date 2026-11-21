import { test } from 'node:test'
import assert from 'node:assert/strict'
import { analyticsDashboardUrl } from './analyticsDashboard.js'

test('the admin page links to the Matomo dashboard when its address is configured', () => {
  assert.equal(analyticsDashboardUrl({ VITE_MATOMO_URL: 'https://analytics.aidea-hub.eu/' }),
    'https://analytics.aidea-hub.eu/')
  assert.equal(analyticsDashboardUrl({ VITE_MATOMO_URL: 'https://analytics.aidea-hub.eu' }),
    'https://analytics.aidea-hub.eu/')
})

test('no analytics link when Matomo is not configured', () => {
  assert.equal(analyticsDashboardUrl({}), null)
  assert.equal(analyticsDashboardUrl({ VITE_MATOMO_URL: '  ' }), null)
  assert.equal(analyticsDashboardUrl(undefined), null)
})
