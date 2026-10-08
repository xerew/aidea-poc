import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Upload, Trash2, Eye, EyeOff } from 'lucide-react'
import client from '../../api/client'
import { LANGUAGES } from '../../i18n'
import H5PFrame from '../lesson/H5PFrame'
import './H5PPanel.css'

const mb = (bytes) => (bytes / (1024 * 1024)).toFixed(1)
const typeName = (lib) => (lib || '').replace(/^H5P\./, '')
const languageLabel = (code) => LANGUAGES.find(l => l.code === code)?.label ?? code

/** H5P resource: main .h5p, optional language versions, self-complete toggle
 *  and an in-page (sandboxed) preview. */
export default function H5PPanel({ resource, uploadUrl, locked, onChange, onRefresh }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState('')         // language being uploaded
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(false)
  const [newLang, setNewLang] = useState('')
  const packages = resource.h5p_packages ?? []
  const main = packages.find(p => p.language === '')
  const versions = packages.filter(p => p.language !== '')
  const free = LANGUAGES.filter(l => !versions.some(v => v.language === l.code))

  const upload = async (file, language) => {
    if (!file) return
    setError('')
    setBusy(language || 'main')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('language', language)
      const res = await client.post(uploadUrl, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      onRefresh(res.data)
      setNewLang('')
    } catch (err) {
      const code = err.response?.data?.code
      setError(t(`authoring.h5p.errors.${code}`, { defaultValue: t('authoring.h5p.errors.generic') }))
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
      setError(t('authoring.h5p.errors.generic'))
    }
  }

  const fileButton = (language, label) => (
    <label className="lesson-upload-btn">
      <Upload size={14} />
      {busy === (language || 'main') ? t('authoring.h5p.uploading') : label}
      <input type="file" hidden accept=".h5p" disabled={Boolean(busy)}
        onChange={(e) => { upload(e.target.files?.[0], language); e.target.value = '' }} />
    </label>
  )

  return (
    <div className="h5p-panel">
      {main ? (
        <div className="h5p-package">
          <div className="h5p-package-info">
            <strong>{main.title || typeName(main.main_library)}</strong>
            <span className="h5p-package-meta">
              {typeName(main.main_library)} · {mb(main.size_bytes)} MB · {t('authoring.h5p.version', { n: main.version })}
            </span>
          </div>
          <div className="h5p-package-actions">
            <button type="button" className="me-media-btn" onClick={() => setPreview(p => !p)}>
              {preview ? <EyeOff size={14} /> : <Eye size={14} />} {preview ? t('authoring.h5p.hidePreview') : t('authoring.h5p.preview')}
            </button>
            {!locked && fileButton('', t('authoring.h5p.replace'))}
          </div>
        </div>
      ) : (
        !locked && fileButton('', t('authoring.h5p.upload'))
      )}
      {preview && main && (
        <div className="h5p-preview">
          <H5PFrame
            key={`${main.id}-${main.version}`}
            pkg={{ package_id: main.id, version: main.version, path: main.path }}
            title={main.title || 'H5P'}
          />
        </div>
      )}

      {main && (
        <div className="h5p-versions">
          <p className="lesson-field-label">{t('authoring.h5p.languageVersions')}</p>
          <p className="h5p-hint">{t('authoring.h5p.languageVersionsHint')}</p>
          {versions.map(v => (
            <div key={v.language} className="h5p-version-row">
              <span className="h5p-version-lang">{languageLabel(v.language)}</span>
              <span className="h5p-package-meta">{v.title} · {t('authoring.h5p.version', { n: v.version })}</span>
              {!locked && fileButton(v.language, t('authoring.h5p.replace'))}
              {!locked && (
                <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => remove(v.language)}
                  title={t('authoring.h5p.remove')}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          {!locked && free.length > 0 && (
            <div className="h5p-version-row">
              <select value={newLang} onChange={(e) => setNewLang(e.target.value)}>
                <option value="">{t('authoring.h5p.addLanguage')}</option>
                {free.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
              {newLang && fileButton(newLang, t('authoring.h5p.upload'))}
            </div>
          )}
        </div>
      )}

      <label className="resource-editor-required">
        <input type="checkbox" checked={Boolean(resource.h5p_self_complete)} disabled={locked}
          onChange={(e) => onChange('h5p_self_complete', e.target.checked)} />
        {t('authoring.h5p.selfComplete')}
      </label>
      <p className="h5p-hint">{t('authoring.h5p.selfCompleteHint')}</p>
      {error && <p className="media-item-error">{error}</p>}
    </div>
  )
}

H5PPanel.propTypes = {
  resource: PropTypes.shape({
    h5p_packages: PropTypes.array,
    h5p_self_complete: PropTypes.bool,
  }).isRequired,
  uploadUrl: PropTypes.string.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onRefresh: PropTypes.func.isRequired,
}
