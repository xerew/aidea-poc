import client from '../../api/client'
import { elapsedSeconds, isActive, pickTarget } from './attention'
import { pageContext } from './context'
import { coveredPct, createRangeRecorder } from './coverage'
import { createLedger } from './ledger'

const TICK_MS = 1000
const FLUSH_MS = 30000
const ENDPOINT = '/tracking/'
const INPUT_EVENTS = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart', 'scroll', 'input']

const accessToken = () => localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
const tenth = (n) => Math.round(n * 10) / 10

// Measures how the learner uses the resources of one activity page (elements
// with data-resource-id inside `root`) and sends it every 30 s and when the
// page is hidden or left. See docs/superpowers/specs/2026-10-01-learning-analytics-design.md.
export function createTracker({ root, language }) {
  const newKey = () => crypto.randomUUID()
  const ledger = createLedger({ pageKey: newKey(), newKey, context: pageContext(language) })
  const visiblePx = new Map()   // resourceId → visible height in px
  const playing = []            // resourceIds with a playing video, most recent last
  const recorders = new Map()   // resourceId → played-range recorder
  let lastInputAt = Date.now()
  let lastResourceInput = null
  let lastTick = Date.now()
  let stopped = false
  let inFlight = false

  const onInput = (e) => {
    lastInputAt = Date.now()
    const el = e.target instanceof Element ? e.target.closest('[data-resource-id]') : null
    if (el && root.contains(el)) lastResourceInput = { resourceId: Number(el.dataset.resourceId), at: lastInputAt }
  }

  const tick = () => {
    const now = Date.now()
    const visible = document.visibilityState === 'visible'
    const seconds = elapsedSeconds(lastTick, now, visible)
    lastTick = now
    if (stopped || seconds === 0) return
    const target = pickTarget({ playing, lastResourceInput, visiblePx, now })
    if (target != null) ledger.addTime(target, seconds, isActive({ visible, lastInputAt, playing, now }))
  }

  const post = async (body, keepalive) => {
    if (!keepalive) return (await client.post(ENDPOINT, body)).status
    // keepalive lets the request finish after the page is gone.
    const token = accessToken()
    const res = await fetch(`${client.defaults.baseURL}${ENDPOINT}`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }) },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(String(res.status))
    return res.status
  }

  const flush = async ({ keepalive = false } = {}) => {
    tick()
    if (stopped || ledger.isEmpty() || (inFlight && !keepalive)) return
    const body = ledger.payload()
    inFlight = true
    try {
      const status = await post(body, keepalive)
      if (status === 204) stop() // tracking switched off by an admin
      else ledger.ack(body)
    } catch {
      // Kept: the next message carries the same totals and events.
    } finally {
      inFlight = false
    }
  }

  const onVisibility = () => {
    if (document.visibilityState === 'hidden') flush({ keepalive: true })
    else lastTick = Date.now()
  }
  const onPageHide = () => flush({ keepalive: true })

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      visiblePx.set(Number(entry.target.dataset.resourceId), entry.isIntersecting ? entry.intersectionRect.height : 0)
    }
  }, { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] })
  root.querySelectorAll('[data-resource-id]').forEach(el => observer.observe(el))

  INPUT_EVENTS.forEach(type => window.addEventListener(type, onInput, { passive: true, capture: true }))
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pagehide', onPageHide)
  const ticker = setInterval(tick, TICK_MS)
  const flusher = setInterval(() => flush(), FLUSH_MS)

  function stop() {
    stopped = true
    clearInterval(ticker)
    clearInterval(flusher)
    observer.disconnect()
    INPUT_EVENTS.forEach(type => window.removeEventListener(type, onInput, { capture: true }))
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('pagehide', onPageHide)
  }

  const setPlaying = (resourceId, on) => {
    const i = playing.indexOf(resourceId)
    if (i >= 0) playing.splice(i, 1)
    if (on) playing.push(resourceId)
  }

  const video = (resourceId, e) => {
    if (stopped) return
    let rec = recorders.get(resourceId)
    if (!rec) { rec = createRangeRecorder(); recorders.set(resourceId, rec) }
    switch (e.type) {
      case 'play':
        setPlaying(resourceId, true)
        rec.sample(e.position)
        ledger.addEvent(resourceId, 'video_play', { position: tenth(e.position) })
        break
      case 'pause':
        setPlaying(resourceId, false)
        rec.cut()
        ledger.addEvent(resourceId, 'video_pause', { position: tenth(e.position) })
        break
      case 'seek':
        rec.cut()
        rec.sample(e.to)
        ledger.addEvent(resourceId, 'video_seek', { from: tenth(e.from), to: tenth(e.to) })
        break
      case 'ended':
        setPlaying(resourceId, false)
        rec.cut()
        ledger.addEvent(resourceId, 'video_ended', { position: tenth(e.position) })
        break
      default:
        rec.sample(e.position)
    }
    if (e.duration > 0) {
      ledger.setMedia(resourceId, {
        covered_pct: coveredPct(rec.ranges(), e.duration),
        furthest_s: Math.round(rec.furthest()),
        duration_s: Math.round(e.duration),
      })
    }
  }

  const api = {
    event: (resourceId, type, data) => { if (!stopped) ledger.addEvent(resourceId, type, data) },
    completed: (resourceId) => { if (!stopped) ledger.markCompleted(resourceId) },
    video,
  }
  return { api, flush, stop }
}
