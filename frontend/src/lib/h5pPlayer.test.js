// Runs public/h5p/player.js in a stand-in window and checks what it hands to
// h5p-standalone and what it tells the parent page.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'

const code = readFileSync(new URL('../../public/h5p/player.js', import.meta.url), 'utf8')

function run({ framed = true, src = 'https://aidea-hub.eu/media/h5p/abc' } = {}) {
  const posted = []
  let options = null
  let onLoad = null
  const window = {
    location: {
      search: `?src=${encodeURIComponent(src)}&channel=c1&origin=https://aidea-hub.eu`,
      href: 'https://aidea-hub.eu/h5p/player.html',
    },
    parent: { postMessage: (message) => posted.push(message) },
    addEventListener: (type, fn) => { if (type === 'load') onLoad = fn },
    localStorage: { getItem: () => null },
    H5PStandalone: {
      H5P: function (el, opts) {
        options = opts
        return { then: () => ({ catch: () => {} }) }
      },
    },
  }
  window.self = window
  window.top = framed ? {} : window
  const document = { getElementById: () => ({}), documentElement: { scrollHeight: 100 }, body: {} }
  vm.runInNewContext(code, { window, document, URL, URLSearchParams, Object, String })
  onLoad()
  return { posted, options }
}

test('content runs in the player window itself (div embed), where the storage shim lives', () => {
  const { options } = run()
  assert.equal(options.embedType, 'div')
  assert.equal(options.h5pJsonPath, 'https://aidea-hub.eu/media/h5p/abc')
})

test('no H5P "user": it makes H5P fetch saved state from a URL we do not have, and crash', () => {
  const { options } = run()
  assert.equal(options.user, undefined)
  assert.equal(options.contentUserData, undefined)
})

test('the player refuses to run unframed or for a package outside /media/h5p/', () => {
  assert.deepEqual(run({ framed: false }).posted.map(m => m.message), ['not framed'])
  assert.deepEqual(run({ src: 'https://evil.example/x' }).posted.map(m => m.message), ['invalid package'])
})
