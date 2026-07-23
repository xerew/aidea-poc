import PropTypes from 'prop-types'
import DOMPurify from 'dompurify'

const looksLikeHtml = (s) => /<\/?[a-z][\s\S]*>/i.test(s)

/**
 * Renders lesson text content. New content is sanitised HTML from the rich-text
 * editor; legacy content is plain text, which we render with preserved line
 * breaks so nothing previously authored loses its formatting.
 */
export default function HtmlContent({ content, className = '' }) {
  const text = content ?? ''
  if (!looksLikeHtml(text)) {
    return <div className={`rich-html rich-html--plain ${className}`}>{text}</div>
  }
  const clean = DOMPurify.sanitize(text, { ADD_ATTR: ['target', 'rel'] })
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
