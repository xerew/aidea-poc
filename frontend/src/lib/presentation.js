// Presentation (.pptx) resources are played by Microsoft's Office viewer,
// which fetches the file itself — so it must be on a public address.

const VIEWER = 'https://view.officeapps.live.com/op/embed.aspx?src='

export const officeViewerUrl = (fileUrl) => VIEWER + encodeURIComponent(fileUrl)

export function absoluteUrl(url, base) {
  return new URL(url, base).href
}

const PRIVATE = [
  /^localhost$/, /\.localhost$/, /\.local$/, /^127\./, /^10\./, /^192\.168\./,
  /^172\.(1[6-9]|2\d|3[01])\./, /^0\.0\.0\.0$/, /^\[?::1\]?$/,
]

/** True when Microsoft's servers could not fetch this address (development). */
export function isPrivateHost(url) {
  let host
  try {
    host = new URL(url).hostname
  } catch {
    return true
  }
  return PRIVATE.some(re => re.test(host))
}

// Same limit as the server (PRESENTATION_MAX_MB); checked before uploading so
// authors are not made to send 100 MB only to be refused.
export const PRESENTATION_MAX_BYTES = 100 * 1024 * 1024

/** The error code to show for a failed upload (Caddy answers 413 before Django sees it). */
export function uploadErrorCode(err) {
  if (err?.response?.status === 413) return 'too_large'
  return err?.response?.data?.code ?? 'generic'
}

/** Full screen for the slideshow frame; where element full screen does not
 *  exist (iPhone Safari) the viewer opens in a new tab instead. */
export function openFullscreen(frame, viewerUrl, win = window) {
  if (frame?.requestFullscreen) {
    frame.requestFullscreen().catch(() => {})
    return
  }
  win.open(viewerUrl, '_blank', 'noopener')
}
