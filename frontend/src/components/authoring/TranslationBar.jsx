import { useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Languages, Check, ChevronDown, CloudOff, RefreshCw } from 'lucide-react'
import client from '../../api/client'
import { LANGUAGES } from '../../i18n'
import { isFinished, isRunning, retranslateOptions, statusLabelKey } from '../../lib/translationUi'
import './TranslationBar.css'

const POLL_INTERVAL_MS = 3000

/**
 * Course-level language switch + translate/re-translate control, shared by
 * CourseEditorPage and ModuleEditorPage. Owns the POST /translate/ call and
 * the polling loop against GET /authoring/courses/<id>/ — callers only need
 * to react to `onStatusUpdate` (live translation_status) and `onTranslated`
 * (fired once a triggered job resolves to 'done'/'reviewed'/'failed', so the
 * caller can reload the translated field content).
 *
 * Re-translate offers the scopes of the page it sits on (`page`, `moduleId`,
 * `activityId`): this activity / this module / whole course in the module
 * editor, course details / whole course in the course editor. Parts
 * machine-translated since the language was marked reviewed are listed as
 * "N to re-check".
 */
export default function TranslationBar({
  courseId, sourceLanguage, translationStatus = {}, activeLang,
  onSelectLang, onStatusUpdate, onTranslated, disabled = false,
  page = 'course', moduleId = null, activityId = null, onOpenItem = null,
}) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  // Last known status of the NTUA translation server: {online, error, since, checked_at}.
  const [service, setService] = useState(null)
  const [checking, setChecking] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [recheck, setRecheck] = useState([])
  const [showRecheck, setShowRecheck] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    client.get('/authoring/translation-service/')
      .then((res) => setService(res.data))
      .catch(() => {})
  }, [])

  const recheckService = async () => {
    setChecking(true)
    try {
      const res = await client.get('/authoring/translation-service/', { params: { refresh: 1 } })
      setService(res.data)
    } catch { /* keep the last known status */ } finally {
      setChecking(false)
    }
  }

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
    setMenuOpen(false)
    setShowRecheck(false)
    onSelectLang(lang)
  }

  const startPolling = (lang) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const res = await client.get(`/authoring/courses/${courseId}/`)
        const status = res.data.translation_status ?? {}
        onStatusUpdate(status)
        if (isFinished(status[lang])) {
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

  const otherLanguages = LANGUAGES.filter((l) => l.code !== sourceLanguage)
  const sourceLabel = LANGUAGES.find((l) => l.code === sourceLanguage)?.label ?? sourceLanguage
  const activeLabel = LANGUAGES.find((l) => l.code === activeLang)?.label ?? activeLang
  const activeStatus = activeLang !== 'original' ? translationStatus?.[activeLang] : null
  const translated = activeStatus === 'done' || activeStatus === 'reviewed'

  // Parts machine-translated since the last review, refreshed whenever the
  // language or its status changes (e.g. an update job just finished).
  useEffect(() => {
    if (activeLang === 'original' || !['done', 'reviewed'].includes(activeStatus)) return undefined
    let alive = true
    client.get(`/authoring/courses/${courseId}/translation-changes/`, { params: { language: activeLang } })
      .then((res) => { if (alive) setRecheck(res.data.items ?? []) })
      .catch(() => {})
    return () => { alive = false }
  }, [courseId, activeLang, activeStatus])
  const visibleRecheck = translated ? recheck : []

  const translateFirst = async (lang) => {
    setBusy(true)
    try {
      const res = await client.post(`/authoring/courses/${courseId}/translate/`, { language: lang })
      setService((s) => (s ? { ...s, online: true } : s))
      onStatusUpdate(res.data.translation_status ?? { ...translationStatus, [lang]: 'pending' })
      startPolling(lang)
    } catch (err) {
      // 503: the server checked the translation service and it is down.
      if (err.response?.status === 503 && err.response.data?.service) setService(err.response.data.service)
      setBusy(false)
    }
  }

  const retranslate = async (option) => {
    setMenuOpen(false)
    let edited = 0
    try {
      const res = await client.get(`/authoring/courses/${courseId}/translation-changes/`,
        { params: { language: activeLang, edited: 1, ...option } })
      edited = res.data.edited_count ?? 0
    } catch { /* confirm without the count */ }
    const scopeName = t(`authoring.translate.scopeName.${option.scope}`)
    const message = edited > 0
      ? t('authoring.translate.reconfirmEdited', { scope: scopeName, count: edited, language: activeLabel })
      : t('authoring.translate.reconfirmScope', { scope: scopeName, language: activeLabel })
    if (!window.confirm(message)) return
    setBusy(true)
    try {
      const res = await client.post(`/authoring/courses/${courseId}/translate/`, { language: activeLang, ...option })
      setService((s) => (s ? { ...s, online: true } : s))
      onStatusUpdate(res.data.translation_status ?? translationStatus)
      startPolling(activeLang)
    } catch (err) {
      if (err.response?.status === 503 && err.response.data?.service) setService(err.response.data.service)
      setBusy(false)
    }
  }

  const reviewTranslation = async (lang, reviewed) => {
    setBusy(true)
    try {
      const res = await client.post(
        `/authoring/courses/${courseId}/translation-review/`, { language: lang, reviewed },
      )
      const status = res.data.translation_status ?? {}
      onStatusUpdate(status)
      setRecheck([])
      setShowRecheck(false)
      onTranslated(lang, status[lang])   // reload the items' flags, so the badges clear too
    } catch { /* ignore */ } finally {
      setBusy(false)
    }
  }

  const recheckLink = (item) => (item.kind === 'course' || !item.module_id
    ? `/authoring/courses/${courseId}`
    : `/authoring/courses/${courseId}/modules/${item.module_id}${item.activity_id ? `?activity=${item.activity_id}` : ''}`)

  const formatTime = (iso) => (iso ? new Date(iso).toLocaleString() : '')

  return (
    <div className="translation-bar">
      {service && !service.online && (
        <div className="translation-service-offline" role="status">
          <CloudOff size={16} />
          <div>
            <strong>{t('authoring.translate.serviceOffline')}</strong>
            <span>
              {t('authoring.translate.serviceOfflineDetails', {
                since: formatTime(service.since), checked: formatTime(service.checked_at),
              })}
            </span>
          </div>
          <button type="button" className="add-dashed-btn" onClick={recheckService} disabled={checking}>
            <RefreshCw size={13} /> {checking ? t('authoring.translate.checking') : t('authoring.translate.checkAgain')}
          </button>
        </div>
      )}
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
                {t(statusLabelKey(st))}
              </span>
            </button>
          )
        })}
      </div>

      {activeLang !== 'original' && (
        <div className="translation-bar-action">
          {isRunning(activeStatus) ? (
            <span className="translation-translating">
              {t(activeStatus === 'updating' ? 'authoring.translate.updating' : 'authoring.translate.translating')}
            </span>
          ) : (
            <>
              {activeStatus === 'done' && <p className="translation-review-note">{t('authoring.translate.reviewNote')}</p>}
              {activeStatus === 'reviewed' && (
                <p className="translation-reviewed-note">
                  <Check size={14} /> {t('authoring.translate.reviewedNote')}
                </p>
              )}
              {activeStatus === 'failed' && <p className="translation-failed-note">{t('authoring.translate.translateFailed')}</p>}

              {visibleRecheck.length > 0 && (
                <div className="translation-recheck">
                  <button type="button" className="translation-recheck-toggle" aria-expanded={showRecheck}
                          onClick={() => setShowRecheck((v) => !v)}>
                    {t('authoring.translate.recheckCount', { count: visibleRecheck.length })}
                    <ChevronDown size={13} />
                  </button>
                  {showRecheck && (
                    <ul className="translation-recheck-list">
                      {visibleRecheck.map((item) => (
                        <li key={`${item.kind}-${item.id}`}>
                          <Link to={recheckLink(item)}
                                onClick={(e) => { if (onOpenItem?.(item)) e.preventDefault() }}>
                            <span className="translation-recheck-kind">{t(`authoring.translate.kind.${item.kind}`)}</span>
                            {item.title}
                          </Link>
                          {item.replaced_edit && (
                            <span className="translation-recheck-replaced">{t('authoring.translate.correctionsReplaced')}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {!disabled && (
                <div className="translation-actions">
                  {/* Human review: valid once a person confirms the LLM output. */}
                  {activeStatus === 'done' && (
                    <button type="button" className="translation-review-btn" disabled={busy}
                            onClick={() => reviewTranslation(activeLang, true)}>
                      <Check size={14} /> {t('authoring.translate.markReviewed')}
                    </button>
                  )}
                  {activeStatus === 'reviewed' && visibleRecheck.length > 0 && (
                    <button type="button" className="translation-review-btn" disabled={busy}
                            onClick={() => reviewTranslation(activeLang, true)}>
                      <Check size={14} /> {t('authoring.translate.markReviewedAgain')}
                    </button>
                  )}
                  {activeStatus === 'reviewed' && (
                    <button type="button" className="add-dashed-btn" disabled={busy}
                            onClick={() => reviewTranslation(activeLang, false)}>
                      {t('authoring.translate.unmarkReviewed')}
                    </button>
                  )}
                  {translated ? (
                    <div className="translation-menu-wrap">
                      <button type="button" className="add-dashed-btn" disabled={busy} aria-haspopup="menu"
                              aria-expanded={menuOpen} onClick={() => setMenuOpen((v) => !v)}>
                        {t('authoring.translate.retranslate')} <ChevronDown size={13} />
                      </button>
                      {menuOpen && (
                        <div className="translation-menu" role="menu">
                          {retranslateOptions({ page, moduleId, activityId }).map((o) => (
                            <button key={o.scope} type="button" role="menuitem" onClick={() => retranslate(o)}>
                              {t(`authoring.translate.scope.${o.scope}`)}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <button type="button" className="add-dashed-btn" disabled={busy}
                            onClick={() => translateFirst(activeLang)}>
                      {t('authoring.translate.translateTo', { language: activeLabel })}
                    </button>
                  )}
                </div>
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
  page: PropTypes.oneOf(['course', 'module']),
  moduleId: PropTypes.number,
  activityId: PropTypes.number,
  // (item) => true when the page handled the re-check entry itself (no navigation).
  onOpenItem: PropTypes.func,
}
