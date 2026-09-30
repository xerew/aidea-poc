import { useEffect, useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { X, Search, Copy } from 'lucide-react'
import client from '../../api/client'
import './ModuleLibraryModal.css'

/**
 * Pick a module from another course and append a copy of it (with its
 * activities and resources) to this course.
 */
export default function ModuleLibraryModal({ courseId, onClose, onImported }) {
  const { t } = useTranslation()
  const [modules, setModules] = useState(null)
  const [query, setQuery] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/authoring/module-library/', { params: { exclude_course: courseId } })
      .then((res) => setModules(res.data))
      .catch(() => setError(t('authoring.editor.moduleLibraryLoadFailed')))
  }, [courseId, t])

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Group the filtered modules under their course.
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    const byCourse = new Map()
    for (const m of modules ?? []) {
      if (q && !`${m.title} ${m.course_title}`.toLowerCase().includes(q)) continue
      if (!byCourse.has(m.course_id)) {
        byCourse.set(m.course_id, { title: m.course_title, published: m.course_published, modules: [] })
      }
      byCourse.get(m.course_id).modules.push(m)
    }
    return [...byCourse.values()]
  }, [modules, query])

  const importModule = async (moduleId) => {
    setBusyId(moduleId)
    setError('')
    try {
      const res = await client.post(`/authoring/courses/${courseId}/modules/import/`, { module_id: moduleId })
      onImported(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('authoring.editor.importFailed'))
      setBusyId(null)
    }
  }

  return (
    <div className="mlib-backdrop" onClick={onClose} role="presentation">
      <div
        className="mlib-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mlib-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mlib-header">
          <h2 id="mlib-title">{t('authoring.editor.moduleLibraryTitle')}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t('common.cancel')}>
            <X size={18} />
          </button>
        </div>
        <p className="mlib-hint">{t('authoring.editor.moduleLibraryHint')}</p>

        <div className="mlib-search">
          <Search size={15} />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('authoring.editor.moduleLibrarySearch')}
          />
        </div>

        {error && <p className="field-error">{error}</p>}

        <div className="mlib-list">
          {modules === null && !error && <p className="mlib-empty">{t('common.loading')}</p>}
          {modules !== null && groups.length === 0 && (
            <p className="mlib-empty">{t('authoring.editor.moduleLibraryEmpty')}</p>
          )}
          {groups.map((g) => (
            <section key={g.title} className="mlib-group">
              <h3>
                {g.title}
                {!g.published && <span className="mlib-draft">{t('authoring.editor.moduleLibraryDraft')}</span>}
              </h3>
              {g.modules.map((m) => (
                <div key={m.id} className="mlib-row">
                  <div className="mlib-row-body">
                    <span className="mlib-row-title">{m.title || '—'}</span>
                    <span className="mlib-row-meta">
                      {t('authoring.editor.moduleLibraryActivities', { count: m.activity_count })}
                      {m.duration_minutes > 0 && ` · ${t('common.minutesLabel', { count: m.duration_minutes })}`}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="enroll-btn enroll-btn--outline mlib-import"
                    disabled={busyId !== null}
                    onClick={() => importModule(m.id)}
                  >
                    <Copy size={14} />
                    {busyId === m.id ? t('authoring.editor.importing') : t('authoring.editor.importModule')}
                  </button>
                </div>
              ))}
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}

ModuleLibraryModal.propTypes = {
  courseId: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  onImported: PropTypes.func.isRequired,
}
