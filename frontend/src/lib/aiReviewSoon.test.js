import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'

const dir = new URL('../locales/', import.meta.url)
const locales = readdirSync(dir).filter(f => f.endsWith('.json'))

test('every language has the AI reviewer "coming soon" label shown to non-admin authors', () => {
  assert.equal(locales.length, 9)
  for (const file of locales) {
    const aiReview = JSON.parse(readFileSync(new URL(file, dir), 'utf8')).authoring.aiReview
    const label = aiReview.enableSoon
    assert.ok(typeof label === 'string', `${file}: authoring.aiReview.enableSoon missing`)
    assert.ok(label.startsWith(aiReview.enable), `${file}: should be the normal label plus the bracket`)
    assert.match(label, / \([^)]+\)$/, `${file}: should end with "(coming soon)" in brackets`)
  }
})
