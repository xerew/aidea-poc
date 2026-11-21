import { test } from 'node:test'
import assert from 'node:assert/strict'
import { inlineParts } from './inline.js'

const LANGS = ['en', 'el', 'fr', 'es', 'it', 'fi', 'sv', 'no', 'de']
const load = async (lng) => (await import(`./${lng}.js`)).default
const shape = (doc) => doc.sections.map(s => s.blocks.map(b => {
  const kind = Object.keys(b)[0]
  const texts = kind === 'ul' ? b.ul : [b[kind]]
  return `${kind}:${texts.length}:${texts.map(x => `${(x.match(/\*\*/g) || []).length}/${(x.match(/info@aidea-hub\.eu/g) || []).length}`).join(',')}`
}).join('|'))

test('the privacy policy exists in all 9 languages with the same structure as English', async () => {
  const en = await load('en')
  assert.equal(en.sections.length, 15)
  for (const lng of LANGS) {
    const doc = await load(lng)
    assert.ok(doc.intro.trim(), `${lng}: intro`)
    assert.deepEqual(shape(doc), shape(en), `${lng}: sections, lists, bold text or contact address differ`)
    doc.sections.forEach((s, i) => assert.match(s.title, new RegExp(`^${i + 1}\\. \\S`), `${lng}: section ${i + 1} title`))
  }
})

test('bold text and the contact address become formatted parts', () => {
  assert.deepEqual(inlineParts('Write to **us** at info@aidea-hub.eu.'), [
    { text: 'Write to ' }, { bold: 'us' }, { text: ' at ' }, { email: 'info@aidea-hub.eu' }, { text: '.' },
  ])
})
