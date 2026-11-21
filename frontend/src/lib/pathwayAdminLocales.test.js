import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'

const dir = new URL('../locales/', import.meta.url)
const locales = readdirSync(dir).filter(f => f.endsWith('.json'))
const get = (obj, path) => path.split('.').reduce((o, k) => o?.[k], obj)

const KEYS = [
  'admin.pathways.title', 'admin.pathways.description', 'admin.pathways.nonePending',
  'admin.pathways.published', 'admin.pathways.unpublished', 'admin.pathways.lastRebuilt',
  'admin.pathways.button', 'admin.pathways.queuing', 'admin.pathways.queued', 'admin.pathways.failed',
  'home.browseAllCourses', 'pathway.empty.no_match',
]

test('every language has the pathway-rebuild card, short-list link and no-match texts', () => {
  assert.equal(locales.length, 9)
  for (const file of locales) {
    const json = JSON.parse(readFileSync(new URL(file, dir), 'utf8'))
    for (const key of KEYS) assert.equal(typeof get(json, key), 'string', `${file}: ${key} missing`)
    assert.match(get(json, 'admin.pathways.lastRebuilt'), /\{\{date\}\}/, `${file}: lastRebuilt needs {{date}}`)
  }
})
