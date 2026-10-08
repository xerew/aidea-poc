// AIDEA H5P player. Runs ONLY inside the learner page's sandboxed iframe
// (opaque origin: no access to AIDEA's storage or sign-in token). Plays one
// unpacked .h5p with h5p-standalone and posts xAPI statements and its height
// to the parent. See docs/superpowers/specs/2026-10-08-h5p-activities-design.md.
(function () {
  var params = new URLSearchParams(window.location.search)
  var src = params.get('src')
  var channel = params.get('channel')
  var parentOrigin = params.get('origin') || '*'

  function post(kind, extra) {
    var message = { source: 'aidea-h5p', channel: channel, kind: kind }
    for (var key in extra || {}) message[key] = extra[key]
    window.parent.postMessage(message, parentOrigin)
  }

  // Never run as a top-level page, and only play AIDEA's unpacked packages.
  var framed = window.top !== window.self
  var validSrc = false
  try { validSrc = new URL(src).pathname.indexOf('/media/h5p/') === 0 } catch (e) { validSrc = false }

  // Storage throws in an opaque origin; H5P only uses it for an anonymous id
  // and copy/paste, so an in-memory stand-in is enough.
  try { window.localStorage.getItem('probe') } catch (e) {
    var memory = {}
    var shim = {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(memory, k) ? memory[k] : null },
      setItem: function (k, v) { memory[k] = String(v) },
      removeItem: function (k) { delete memory[k] },
      clear: function () { memory = {} },
    }
    try { Object.defineProperty(window, 'localStorage', { value: shim, configurable: true }) } catch (e2) { /* keep going */ }
  }

  function reportHeight() {
    post('height', { height: document.documentElement.scrollHeight })
  }

  window.addEventListener('load', function () {
    if (!framed || !validSrc || !window.H5PStandalone) {
      post('error', { message: !framed ? 'not framed' : !validSrc ? 'invalid package' : 'player missing' })
      return
    }
    var vendor = new URL('vendor/', window.location.href).href
    new window.H5PStandalone.H5P(document.getElementById('h5p'), {
      h5pJsonPath: src,
      frameJs: vendor + 'frame.bundle.js',
      frameCss: vendor + 'styles/h5p.css',
      fullScreen: true,
      // A fixed actor keeps H5P away from storage for an anonymous id; AIDEA
      // knows the learner from the page, not from the statement.
      user: { name: 'AIDEA learner', mail: 'learner@aidea-hub.eu' },
    }).then(function () {
      window.H5P.externalDispatcher.on('xAPI', function (event) {
        try {
          post('xapi', { statement: JSON.parse(JSON.stringify(event.data.statement)) })
        } catch (e) { /* not serialisable: skip */ }
      })
      post('ready')
      reportHeight()
      if (window.ResizeObserver) new window.ResizeObserver(reportHeight).observe(document.body)
      else window.setInterval(reportHeight, 1000)
    }).catch(function (err) {
      post('error', { message: String((err && err.message) || err).slice(0, 200) })
    })
  })
})()
