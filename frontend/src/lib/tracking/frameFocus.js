// Clicks inside a cross-origin frame (Microsoft's slideshow viewer) never
// reach our page, so "the learner is using the slideshow" is read from focus:
// while our window is blurred, focus is checked every second; it counts as
// attending while it sits in this frame, until it moves elsewhere (back to the
// page, or straight into another iframe such as a video) or PRESENTATION_FOCUS_MS
// passes — a deck left open on screen must not count forever.

export const PRESENTATION_FOCUS_MS = 5 * 60 * 1000
const POLL_MS = 1000

export function watchFrameFocus(frame, onChange, {
  win = window, doc = document, capMs = PRESENTATION_FOCUS_MS,
  setTimer = setTimeout, clearTimer = clearTimeout,
} = {}) {
  let attending = false
  let capped = false        // this stay in the frame used up its time
  let capTimer = null
  let pollTimer = null
  const set = (on) => {
    if (on !== attending) { attending = on; onChange(on) }
  }
  const clearCap = () => {
    if (capTimer != null) { clearTimer(capTimer); capTimer = null }
  }
  const clearPoll = () => {
    if (pollTimer != null) { clearTimer(pollTimer); pollTimer = null }
  }
  const check = () => {
    const inFrame = doc.activeElement === frame
    if (inFrame && !attending && !capped) {
      set(true)
      capTimer = setTimer(() => { capTimer = null; capped = true; set(false) }, capMs)
    } else if (!inFrame) {
      clearCap()
      capped = false
      set(false)
    }
  }
  const poll = (delay) => {
    pollTimer = setTimer(() => { pollTimer = null; check(); poll(POLL_MS) }, delay)
  }
  // activeElement moves to the iframe just after the window's blur event.
  const onBlur = () => { clearPoll(); poll(0) }
  const onFocus = () => { clearPoll(); clearCap(); capped = false; set(false) }
  win.addEventListener('blur', onBlur)
  win.addEventListener('focus', onFocus)
  return () => {
    win.removeEventListener('blur', onBlur)
    win.removeEventListener('focus', onFocus)
    clearPoll()
    clearCap()
    set(false)
  }
}
