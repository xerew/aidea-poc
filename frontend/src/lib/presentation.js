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
