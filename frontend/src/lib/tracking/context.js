// Context sent once per visit: no IP address, no precise location.

export function deviceFromUserAgent(ua, touchPoints) {
  if (/iPhone|iPod|Android.+Mobile|Mobi/i.test(ua)) return 'mobile'
  if (/iPad|Tablet|Android/i.test(ua)) return 'tablet'
  if (/Macintosh/.test(ua) && touchPoints > 1) return 'tablet' // iPadOS reports a Mac
  return 'desktop'
}

export function pageContext(
  language,
  now = new Date(),
  ua = globalThis.navigator?.userAgent ?? '',
  touchPoints = globalThis.navigator?.maxTouchPoints ?? 0,
) {
  return {
    language: (language || '').slice(0, 8),
    device: deviceFromUserAgent(ua, touchPoints),
    local_hour: now.getHours(),
    tz_offset_minutes: -now.getTimezoneOffset(), // minutes ahead of UTC (Athens summer = 180)
  }
}
