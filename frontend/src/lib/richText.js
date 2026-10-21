// One list of what rich text may contain — used by the editor (TinyMCE
// valid_elements) and the learner view (DOMPurify). Spec 2026-10-21 §1.

export const RICH_TEXT_VALID_ELEMENTS = [
  'p,br,strong/b,em/i,u,h2,h3,ul,ol,li,a[href|target|rel],blockquote',
  'table,thead,tbody,tr,th[colspan|rowspan|scope],td[colspan|rowspan],caption',
  'img[src|alt|width|height]',
].join(',')

export const SANITIZE_CONFIG = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'blockquote',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'img'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'width', 'height', 'colspan', 'rowspan', 'scope'],
}

const LOCAL_DEV = /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?\//i

/** https images, our uploaded /media/ files, and local development uploads. */
export function isAllowedImageSrc(src) {
  if (typeof src !== 'string') return false
  const value = src.trim()
  return /^https:\/\//i.test(value) || /^\/media\//.test(value) || LOCAL_DEV.test(value)
}
