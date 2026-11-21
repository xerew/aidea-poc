import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createLatest } from './latestRequest.js'

test('only the newest request counts, so a slow older one cannot overwrite it', () => {
  const latest = createLatest()
  const loadMore = latest.start()
  const switchFilter = latest.start()
  assert.equal(latest.isCurrent(loadMore), false)
  assert.equal(latest.isCurrent(switchFilter), true)
})
