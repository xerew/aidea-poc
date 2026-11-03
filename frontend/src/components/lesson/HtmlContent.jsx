import PropTypes from 'prop-types'
import { createRichHtmlSanitizer } from '../../lib/sanitizeRichHtml'
import '../../styles/richContent.css'

const looksLikeHtml = (s) => /<\/?[a-z][\s\S]*>/i.test(s)

// Allowed formatting only (lib/richTextStyles.js), safe images, tables wrapped for scrolling.
const sanitize = createRichHtmlSanitizer(window)

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
  const clean = sanitize(text)
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
