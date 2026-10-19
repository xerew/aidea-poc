// Clicks inside a cross-origin frame (Microsoft's slideshow viewer) never
// reach our page, so "the learner is using the slideshow" is read from focus:
// when the window loses focus to this frame, it counts as attending, until
// focus comes back or PRESENTATION_FOCUS_MS passes (a deck left open on screen
// must not count forever).

export const PRESENTATION_FOCUS_MS = 5 * 60 * 1000

export function watchFrameFocus(frame, onChange, {
  win = window, doc = document, capMs = PRESENTATION_FOCUS_MS,
  setTimer = setTimeout, clearTimer = clearTimeout,
} = {}) {
  let attending = false
  let capTimer = null
  let checkTimer = null
  const set = (on) => {
    if (on !== attending) { attending = on; onChange(on) }
  }
  const clearCap = () => {
    if (capTimer != null) { clearTimer(capTimer); capTimer = null }
  }
  const onBlur = () => {
    // activeElement moves to the iframe just after the window's blur event.
    checkTimer = setTimer(() => {
      checkTimer = null
      if (doc.activeElement !== frame) return
      set(true)
      clearCap()
      capTimer = setTimer(() => { capTimer = null; set(false) }, capMs)
    }, 0)
  }
  const onFocus = () => { clearCap(); set(false) }
  win.addEventListener('blur', onBlur)
  win.addEventListener('focus', onFocus)
  return () => {
    win.removeEventListener('blur', onBlur)
    win.removeEventListener('focus', onFocus)
    if (checkTimer != null) clearTimer(checkTimer)
    clearCap()
    set(false)
  }
}
