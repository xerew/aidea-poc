import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Copy, ChevronDown, ChevronUp } from 'lucide-react'
import HtmlContent from '../lesson/HtmlContent'
import './OriginalHint.css'

// Plain text longer than this (or spanning lines) starts clamped to 3 lines.
const LONG_TEXT = 180

/**
 * Shown under a field while translating: the original (source-language) text
 * the translator is working from, with a one-click Copy into the field.
 * Nothing is pre-filled, so untranslated source text is never saved as a
 * translation by accident.
 *
 * - plain text: shown in full, or clamped to 3 lines with "Show more" if long
 * - html (rich text): collapsed behind "Show original"; opens as formatted,
 *   scrollable preview
 */
export default function OriginalHint({ text, onCopy, language, html = false }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  if (!text || !String(text).replace(/<[^>]*>/g, '').trim()) return null

  const copyButton = (
    <button
      type="button"
      className="original-hint-copy"
      onClick={() => onCopy(text)}
      title={t('authoring.translate.copyOriginalTitle')}
    >
      <Copy size={12} /> {t('authoring.translate.copyOriginal')}
    </button>
  )

  if (html) {
    return (
      <div className="original-hint original-hint--html">
        <div className="original-hint-bar">
          <button type="button" className="original-hint-toggle" onClick={() => setOpen((v) => !v)}>
            {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {open
              ? t('authoring.translate.hideOriginal')
              : t('authoring.translate.showOriginal', { language })}
          </button>
          {copyButton}
        </div>
        {open && (
          <div className="original-hint-html">
            <HtmlContent content={text} />
          </div>
        )}
      </div>
    )
  }

  const long = text.length > LONG_TEXT || text.includes('\n')
  return (
    <div className="original-hint">
      <div className="original-hint-bar">
        <span className="original-hint-label">{t('authoring.translate.originalLabel', { language })}</span>
        {copyButton}
      </div>
      <p className={`original-hint-text${long && !open ? ' original-hint-text--clamped' : ''}`}>{text}</p>
      {long && (
        <button type="button" className="original-hint-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? t('authoring.translate.showLess') : t('authoring.translate.showMore')}
        </button>
      )}
    </div>
  )
}

OriginalHint.propTypes = {
  text: PropTypes.string,
  onCopy: PropTypes.func.isRequired,
  language: PropTypes.string.isRequired,
  html: PropTypes.bool,
}
