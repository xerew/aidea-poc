import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BookOpen, Clock, Download, Pencil, Plus, Upload } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './AuthoringPage.css'

const PILLAR_COLOR = {
  'teach-with-ai':  'blue',
  'teach-for-ai':   'purple',
  'teach-about-ai': 'green',
}

export default function AuthoringPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const importInputRef = useRef(null)
  const [transferErrors, setTransferErrors] = useState({ title: '', messages: [] })
  const [importing, setImporting] = useState(false)

  const LEVEL_LABELS = {
    beginner: t('common.level.beginner'),
    intermediate: t('common.level.intermediate'),
    advanced: t('common.level.advanced'),
  }

  useEffect(() => {
    client.get('/authoring/courses/')
      .then((res) => setCourses(res.data))
      .catch(() => setError(t('authoring.loadError')))
      .finally(() => setLoading(false))
  }, [t])

  const handleExport = async (course) => {
    try {
      const res = await client.get(`/authoring/courses/${course.id}/export/`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `${course.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'course'}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      setTransferErrors({ title: t('authoring.exportFailedTitle'), messages: [t('authoring.exportFailedMsg')] })
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const res = await client.get('/authoring/courses/template/', { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'aidea-course-template.xlsx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setTransferErrors({
        title: t('authoring.importFailedTitle'),
        messages: [t('authoring.templateFailedMsg')],
      })
    }
  }

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setTransferErrors({ title: '', messages: [] })
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/courses/import/', fd)
      navigate(`/authoring/courses/${res.data.id}`)
    } catch (err) {
      const errors = err.response?.data?.errors
      setTransferErrors({
        title: t('authoring.importFailedTitle'),
        messages: Array.isArray(errors) ? errors : [t('authoring.importFailedMsg')],
      })
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  if (error) return <p className="page-error">{error}</p>
  if (loading) return <p className="page-loading">{t('common.loading')}</p>

  const byPillar = courses.reduce((acc, course) => {
    const key = course.pillar.id
    if (!acc[key]) acc[key] = { pillar: course.pillar, courses: [] }
    acc[key].courses.push(course)
    return acc
  }, {})

  return (
    <div className="authoring-page">
      <div className="authoring-header">
        <div>
          <h1 className="authoring-title">{t('authoring.title')}</h1>
          <p className="authoring-subtitle">{t('authoring.subtitle')}</p>
        </div>
        <div className="authoring-header-actions">
          <button className="new-course-btn" onClick={() => navigate('/authoring/courses/new')}>
            <Plus size={15} /> {t('authoring.newCourse')}
          </button>
          <button className="authoring-import-btn" onClick={handleDownloadTemplate}>
            <Download size={15} /> {t('authoring.downloadTemplate')}
          </button>
          <button className="authoring-import-btn" onClick={() => importInputRef.current?.click()} disabled={importing}>
            <Upload size={15} /> {importing ? t('authoring.importing') : t('authoring.importCourse')}
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept=".xlsx"
            hidden
            onChange={handleImportFile}
          />
        </div>
      </div>

      {transferErrors.messages.length > 0 && (
        <div className="authoring-import-errors">
          <div className="authoring-import-errors-head">
            <strong>{transferErrors.title}</strong>
            <button
              aria-label={t('authoring.dismissErrors')}
              onClick={() => setTransferErrors({ title: '', messages: [] })}
            >✕</button>
          </div>
          <ul>
            {transferErrors.messages.slice(0, 20).map((msg, i) => <li key={i}>{msg}</li>)}
            {transferErrors.messages.length > 20 && (
              <li>{t('authoring.moreErrors', { count: transferErrors.messages.length - 20 })}</li>
            )}
          </ul>
        </div>
      )}

      {courses.length === 0 && (
        <p className="authoring-empty">{t('authoring.empty')}</p>
      )}

      {Object.values(byPillar).map(({ pillar, courses: pillarCourses }) => (
        <section key={pillar.id} className="authoring-pillar-section">
          <span className={`pillar-badge pillar-badge--${PILLAR_COLOR[pillar.slug] ?? 'blue'}`}>
            {pillar.name}
          </span>
          <div className="authoring-course-list">
            {pillarCourses.map((course) => (
              <div key={course.id} className="authoring-course-row">
                <div className="authoring-course-info">
                  <div className="authoring-course-title-row">
                    <p className="authoring-course-title">{course.title}</p>
                    <span className={`status-badge ${course.is_published ? 'status-badge--published' : 'status-badge--draft'}`}>
                      {course.is_published ? t('authoring.published') : t('authoring.draft')}
                    </span>
                  </div>
                  <div className="authoring-course-meta">
                    <span><Clock size={13} /> {course.duration_hours}h</span>
                    <span><BookOpen size={13} /> {t('common.moduleCount', { count: course.module_count })}</span>
                    <span>{LEVEL_LABELS[course.level] ?? course.level}</span>
                  </div>
                  <p className="course-card-author">{t('authoring.byAuthor', { name: course.created_by_name })}</p>
                </div>
                <div className="authoring-course-actions">
                  <button
                    className="edit-btn"
                    onClick={() => navigate(`/authoring/courses/${course.id}`)}
                  >
                    <Pencil size={14} /> {course.is_published && course.created_by_id !== user?.id && user?.profile?.user_type !== 'admin' ? t('authoring.view') : t('authoring.edit')}
                  </button>
                  <button
                    className="authoring-export-btn"
                    onClick={(e) => { e.stopPropagation(); handleExport(course) }}
                    title={t('authoring.exportTitle')}
                  >
                    <Download size={14} /> {t('authoring.export')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
