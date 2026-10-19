import { test } from 'node:test'
import assert from 'node:assert/strict'
import { absoluteUrl, isPrivateHost, officeViewerUrl } from './presentation.js'

test('office viewer url encodes the file url', () => {
  assert.equal(
    officeViewerUrl('https://aidea-hub.eu/media/presentations/3/ab.pptx?x=1&y=2'),
    'https://view.officeapps.live.com/op/embed.aspx?src=https%3A%2F%2Faidea-hub.eu%2Fmedia%2Fpresentations%2F3%2Fab.pptx%3Fx%3D1%26y%3D2',
  )
})

test('private and development hosts', () => {
  for (const url of ['http://localhost:8000/media/a.pptx', 'http://api.localhost/a', 'http://box.local/a',
    'http://127.0.0.1/a', 'http://10.1.2.3/a', 'http://192.168.0.5/a', 'http://172.16.0.1/a',
    'http://172.31.255.1/a', 'http://0.0.0.0/a', 'http://[::1]/a', 'not a url']) {
    assert.equal(isPrivateHost(url), true, url)
  }
  for (const url of ['https://aidea-hub.eu/media/a.pptx', 'http://172.32.0.1/a', 'http://11.0.0.1/a']) {
    assert.equal(isPrivateHost(url), false, url)
  }
})

test('absolute url resolves site-relative paths against the API origin', () => {
  assert.equal(absoluteUrl('/media/p/a.pptx', 'https://aidea-hub.eu/api'), 'https://aidea-hub.eu/media/p/a.pptx')
  assert.equal(absoluteUrl('https://cdn.example/a.pptx', 'https://aidea-hub.eu/api'), 'https://cdn.example/a.pptx')
})
