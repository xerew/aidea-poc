import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Eye, EyeOff, Trash2, Upload } from 'lucide-react'
import client from '../../api/client'
import { LANGUAGES } from '../../i18n'
import PresentationFrame from '../lesson/PresentationFrame'
import { PRESENTATION_MAX_BYTES, uploadErrorCode } from '../../lib/presentation'
import './PresentationPanel.css'

const mb = (bytes) => (bytes / (1024 * 1024)).toFixed(1)
const languageLabel = (code) => LANGUAGES.find(l => l.code === code)?.label ?? code

/** Presentation resource: main .pptx, optional language versions, download
 *  setting and an in-page preview. */
export default function PresentationPanel({ resource, uploadUrl, locked, onChange, onRefresh }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(false)
  const [newLang, setNewLang] = useState('')
  const decks = resource.presentation_files ?? []
  const main = decks.find(d => d.language === '')
  const versions = decks.filter(d => d.language !== '')
  const free = LANGUAGES.filter(l => !versions.some(v => v.language === l.code))

  const upload = async (file, language) => {
    if (!file) return
    setError('')
    if (file.size > PRESENTATION_MAX_BYTES) {
      setError(t('authoring.presentation.errors.too_large'))
      return
    }
    setBusy(language || 'main')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('language', language)
      const res = await client.post(uploadUrl, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      onRefresh(res.data)
      setNewLang('')
    } catch (err) {
      const code = uploadErrorCode(err)
      setError(t(`authoring.presentation.errors.${code}`, { defaultValue: t('authoring.presentation.errors.generic') }))
    } finally {
      setBusy('')
    }
  }

  const remove = async (language) => {
    setError('')
    try {
      const res = await client.delete(uploadUrl, { params: { language } })
      onRefresh(res.data)
    } catch {
      setError(t('authoring.presentation.errors.generic'))
    }
  }

  const fileButton = (language, label) => (
    <label className="lesson-upload-btn">
      <Upload size={14} />
      {busy === (language || 'main') ? t('authoring.presentation.uploading') : label}
      <input type="file" hidden accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
        disabled={Boolean(busy)} onChange={(e) => { upload(e.target.files?.[0], language); e.target.value = '' }} />
    </label>
  )

  const meta = (d) => `${t('authoring.presentation.slides', { count: d.slide_count })} · ${mb(d.size_bytes)} MB · ${t('authoring.presentation.version', { n: d.version })}`

  return (
    <div className="pres-panel">
      <p className="pres-hint">{t('authoring.presentation.formatHint')}</p>
      {main ? (
        <div className="pres-deck">
          <div className="pres-deck-info">
            <strong>{main.title}</strong>
            <span className="pres-deck-meta">{meta(main)}</span>
          </div>
          <div className="pres-deck-actions">
            <button type="button" className="lesson-upload-btn" onClick={() => setPreview(p => !p)}>
              {preview ? <EyeOff size={14} /> : <Eye size={14} />} {preview ? t('authoring.presentation.hidePreview') : t('authoring.presentation.preview')}
            </button>
            {!locked && fileButton('', t('authoring.presentation.replace'))}
            {!locked && (
              <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => remove('')}
                title={t('authoring.presentation.remove')} aria-label={t('authoring.presentation.remove')}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>
      ) : (
        !locked && fileButton('', t('authoring.presentation.upload'))
      )}
      {main?.over_viewer_limit && (
        <p className="pres-warning"><AlertTriangle size={14} /> {t('authoring.presentation.overLimit')}</p>
      )}
      {preview && main && <PresentationFrame key={`${main.id}-${main.version}`} url={main.path} title={main.title} />}

      {main && (
        <div className="pres-versions">
          <p className="lesson-field-label">{t('authoring.presentation.languageVersions')}</p>
          <p className="pres-hint">{t('authoring.presentation.languageVersionsHint')}</p>
          {versions.map(v => (
            <div key={v.language} className="pres-version-row">
              <span className="pres-version-lang">{languageLabel(v.language)}</span>
              <span className="pres-deck-meta">{v.title} · {meta(v)}</span>
              {v.over_viewer_limit && <AlertTriangle size={14} className="pres-warning-icon" aria-label={t('authoring.presentation.overLimit')} />}
              {!locked && fileButton(v.language, t('authoring.presentation.replace'))}
              {!locked && (
                <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => remove(v.language)}
                  title={t('authoring.presentation.remove')}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          {!locked && free.length > 0 && (
            <div className="pres-version-row">
              <select value={newLang} onChange={(e) => setNewLang(e.target.value)}>
                <option value="">{t('authoring.presentation.addLanguage')}</option>
                {free.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
              {newLang && fileButton(newLang, t('authoring.presentation.upload'))}
            </div>
          )}
        </div>
      )}

      <label className="resource-editor-required">
        <input type="checkbox" checked={Boolean(resource.presentation_downloadable)} disabled={locked}
          onChange={(e) => onChange('presentation_downloadable', e.target.checked)} />
        {t('authoring.presentation.downloadable')}
      </label>
      <p className="pres-hint">{t('authoring.presentation.downloadableHint')}</p>
      {error && <p className="media-item-error">{error}</p>}
    </div>
  )
}

PresentationPanel.propTypes = {
  resource: PropTypes.shape({
    presentation_files: PropTypes.array,
    presentation_downloadable: PropTypes.bool,
  }).isRequired,
  uploadUrl: PropTypes.string.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onRefresh: PropTypes.func.isRequired,
}
