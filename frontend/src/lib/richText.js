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

// TinyMCE rewrites same-origin URLs relative to the editing page by default
// ("../../media/x.png"), which breaks images for learners on other pages.
// Keep them absolute paths ("/media/x.png").
export const EDITOR_URL_OPTIONS = { relative_urls: false, remove_script_host: true, convert_urls: true }

/** TinyMCE image upload via the authoring upload endpoint. A failed upload
 *  removes the image from the editor (remove: true), so nothing is saved that
 *  learners would never see. */
export function makeImageUploader(client) {
  return async (blobInfo) => {
    const form = new FormData()
    form.append('file', blobInfo.blob(), blobInfo.filename())
    try {
      const res = await client.post('/authoring/upload/', form)
      return res.data.url
    } catch (err) {
      throw { message: err.response?.data?.error ?? 'Upload failed.', remove: true }
    }
  }
}
