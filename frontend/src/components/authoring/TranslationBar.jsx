import { useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Languages } from 'lucide-react'
import client from '../../api/client'
import { LANGUAGES } from '../../i18n'
import './TranslationBar.css'

const POLL_INTERVAL_MS = 3000

/**
 * Course-level language switch + translate/re-translate control, shared by
 * CourseEditorPage and ModuleEditorPage. Owns the POST /translate/ call and
 * the polling loop against GET /authoring/courses/<id>/ — callers only need
 * to react to `onStatusUpdate` (live translation_status) and `onTranslated`
 * (fired once a triggered job resolves to 'done'/'failed', so the caller can
 * reload the translated field content).
 */
export default function TranslationBar({
  courseId, sourceLanguage, translationStatus = {}, activeLang,
  onSelectLang, onStatusUpdate, onTranslated, disabled = false,
}) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const pollRef = useRef(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  // Stop polling on unmount.
  useEffect(() => () => stopPolling(), [])

  // Switching the selected language should stop any in-flight polling for
  // the language being left — routed through the tab click handlers below
  // (not a useEffect keyed on activeLang) so this is a plain event reaction
  // rather than a state update synchronized inside an effect.
  const selectLang = (lang) => {
    stopPolling()
    setBusy(false)
    onSelectLang(lang)
  }

  const startPolling = (lang) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const res = await client.get(`/authoring/courses/${courseId}/`)
        const status = res.data.translation_status ?? {}
        onStatusUpdate(status)
        if (status[lang] === 'done' || status[lang] === 'failed') {
          stopPolling()
          setBusy(false)
          onTranslated(lang, status[lang])
        }
      } catch {
        stopPolling()
        setBusy(false)
      }
    }, POLL_INTERVAL_MS)
  }

  const triggerTranslate = async (lang, isRetranslate) => {
    if (isRetranslate && !window.confirm(t('authoring.translate.reconfirm'))) return
    setBusy(true)
    try {
      const res = await client.post(`/authoring/courses/${courseId}/translate/`, { language: lang })
      onStatusUpdate(res.data.translation_status ?? { ...translationStatus, [lang]: 'pending' })
      startPolling(lang)
    } catch {
      setBusy(false)
    }
  }

  const otherLanguages = LANGUAGES.filter((l) => l.code !== sourceLanguage)
  const sourceLabel = LANGUAGES.find((l) => l.code === sourceLanguage)?.label ?? sourceLanguage
  const activeLabel = LANGUAGES.find((l) => l.code === activeLang)?.label ?? activeLang
  const activeStatus = activeLang !== 'original' ? translationStatus?.[activeLang] : null

  return (
    <div className="translation-bar">
      <div className="translation-bar-tabs" role="tablist" aria-label={t('authoring.translate.switchLanguage')}>
        <Languages size={15} className="translation-bar-icon" />
        <button
          type="button"
          role="tab"
          aria-selected={activeLang === 'original'}
          className={`translation-tab${activeLang === 'original' ? ' translation-tab--active' : ''}`}
          title={t('authoring.translate.viewingOriginal')}
          onClick={() => selectLang('original')}
        >
          {t('authoring.translate.originalTabLabel', { language: sourceLabel })}
        </button>
        {otherLanguages.map((l) => {
          const st = translationStatus?.[l.code]
          return (
            <button
              key={l.code}
              type="button"
              role="tab"
              aria-selected={activeLang === l.code}
              className={`translation-tab${activeLang === l.code ? ' translation-tab--active' : ''}`}
              onClick={() => selectLang(l.code)}
            >
              {l.label}
              <span className={`translation-status translation-status--${st ?? 'none'}`}>
                {st === 'pending' && t('authoring.translate.statusPending')}
                {st === 'done' && t('authoring.translate.statusDone')}
                {st === 'failed' && t('authoring.translate.statusFailed')}
                {!st && t('authoring.translate.statusNone')}
              </span>
            </button>
          )
        })}
      </div>

      {activeLang !== 'original' && (
        <div className="translation-bar-action">
          {activeStatus === 'pending' ? (
            <span className="translation-translating">{t('authoring.translate.translating')}</span>
          ) : (
            <>
              {activeStatus === 'done' && <p className="translation-review-note">{t('authoring.translate.reviewNote')}</p>}
              {activeStatus === 'failed' && <p className="translation-failed-note">{t('authoring.translate.translateFailed')}</p>}
              {!disabled && (
                <button
                  type="button"
                  className="add-dashed-btn"
                  disabled={busy}
                  onClick={() => triggerTranslate(activeLang, activeStatus === 'done')}
                >
                  {activeStatus === 'done'
                    ? t('authoring.translate.retranslate')
                    : t('authoring.translate.translateTo', { language: activeLabel })}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

TranslationBar.propTypes = {
  courseId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  sourceLanguage: PropTypes.string.isRequired,
  translationStatus: PropTypes.object,
  activeLang: PropTypes.string.isRequired,
  onSelectLang: PropTypes.func.isRequired,
  onStatusUpdate: PropTypes.func.isRequired,
  onTranslated: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}
