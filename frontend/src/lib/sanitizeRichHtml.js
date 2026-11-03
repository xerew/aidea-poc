import DOMPurify from 'dompurify'
import { SANITIZE_CONFIG, isAllowedImageSrc } from './richText.js'
import { filterClass, filterStyle } from './richTextStyles.js'

/**
 * The learner-view sanitizer (spec 2026-11-03): DOMPurify bound to `win`, with
 * - images only from https, our /media/ uploads or local development;
 * - `style` reduced to the allowed declarations per element, `class` to the
 *   table presets (tables only) — anything else is dropped;
 * - every table wrapped in a scroll container, so a wide table scrolls inside
 *   its own area and the page never scrolls sideways.
 * Returns html → clean html.
 */
export function createRichHtmlSanitizer(win) {
  const purify = DOMPurify(win)

  purify.addHook('uponSanitizeElement', (node, data) => {
    if (data.tagName === 'img' && !isAllowedImageSrc(node.getAttribute('src'))) {
      node.parentNode?.removeChild(node)
    }
  })

  purify.addHook('uponSanitizeAttribute', (node, data) => {
    const tag = node.nodeName.toLowerCase()
    if (data.attrName === 'style') data.attrValue = filterStyle(data.attrValue, tag)
    else if (data.attrName === 'class') data.attrValue = filterClass(data.attrValue, tag)
    else return
    if (!data.attrValue) data.keepAttr = false
  })

  return (html) => {
    const fragment = purify.sanitize(html, { ...SANITIZE_CONFIG, RETURN_DOM_FRAGMENT: true })
    for (const table of fragment.querySelectorAll('table')) {
      const wrapper = win.document.createElement('div')
      wrapper.className = 'rich-table-scroll'
      table.replaceWith(wrapper)
      wrapper.appendChild(table)
    }
    const box = win.document.createElement('div')
    box.appendChild(fragment)
    return box.innerHTML
  }
}
