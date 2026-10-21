import PropTypes from 'prop-types'
import DOMPurify from 'dompurify'
import { SANITIZE_CONFIG, isAllowedImageSrc } from '../../lib/richText'
import './RichTextEditor.css'

const looksLikeHtml = (s) => /<\/?[a-z][\s\S]*>/i.test(s)

// Images are kept only from https, our /media/ uploads or local development.
DOMPurify.addHook('uponSanitizeElement', (node, data) => {
  if (data.tagName === 'img' && !isAllowedImageSrc(node.getAttribute('src'))) {
    node.parentNode?.removeChild(node)
  }
})

/**
 * Renders lesson text content. New content is sanitised HTML from the rich-text
 * editor (the same allow-list as the editor: text formatting, links, tables and
 * images); legacy content is plain text, which we render with preserved line
 * breaks so nothing previously authored loses its formatting.
 */
export default function HtmlContent({ content, className = '' }) {
  const text = content ?? ''
  if (!looksLikeHtml(text)) {
    return <div className={`rich-html rich-html--plain ${className}`}>{text}</div>
  }
  const clean = DOMPurify.sanitize(text, SANITIZE_CONFIG)
  return (
    <div
      className={`rich-html ${className}`}
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  )
}

HtmlContent.propTypes = {
  content: PropTypes.string,
  className: PropTypes.string,
}
