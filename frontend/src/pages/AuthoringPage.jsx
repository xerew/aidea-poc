import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Clock, Download, Pencil, Plus, Upload } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './AuthoringPage.css'

const PILLAR_COLOR = {
  'teach-with-ai':  'blue',
  'teach-for-ai':   'purple',
  'teach-about-ai': 'green',
}

const LEVEL_LABELS = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }

export default function AuthoringPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const importInputRef = useRef(null)
  const [transferErrors, setTransferErrors] = useState({ title: '', messages: [] })
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    client.get('/authoring/courses/')
      .then((res) => setCourses(res.data))
      .catch(() => setError('Failed to load courses. Make sure your account has Content Creator access.'))
      .finally(() => setLoading(false))
  }, [])

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
      setTransferErrors({ title: 'Export failed:', messages: ['Could not download the workbook. Please try again.'] })
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
        title: 'Import failed — fix these and retry:',
        messages: Array.isArray(errors) ? errors : ['Import failed. Please try again.'],
      })
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  if (error) return <p className="page-error">{error}</p>
  if (loading) return <p className="page-loading">Loading…</p>

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
          <h1 className="authoring-title">Course Authoring</h1>
          <p className="authoring-subtitle">Select a course to edit its content.</p>
        </div>
        <div className="authoring-header-actions">
          <button className="new-course-btn" onClick={() => navigate('/authoring/courses/new')}>
            <Plus size={15} /> New Course
          </button>
          <button className="authoring-import-btn" onClick={() => importInputRef.current?.click()} disabled={importing}>
            <Upload size={15} /> {importing ? 'Importing…' : 'Import course'}
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
              aria-label="Dismiss errors"
              onClick={() => setTransferErrors({ title: '', messages: [] })}
            >✕</button>
          </div>
          <ul>
            {transferErrors.messages.slice(0, 20).map((msg, i) => <li key={i}>{msg}</li>)}
            {transferErrors.messages.length > 20 && (
              <li>…and {transferErrors.messages.length - 20} more.</li>
            )}
          </ul>
        </div>
      )}

      {courses.length === 0 && (
        <p className="authoring-empty">No courses yet. Create your first one!</p>
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
                      {course.is_published ? 'Published' : 'Draft'}
                    </span>
                  </div>
                  <div className="authoring-course-meta">
                    <span><Clock size={13} /> {course.duration_hours}h</span>
                    <span><BookOpen size={13} /> {course.module_count} modules</span>
                    <span>{LEVEL_LABELS[course.level] ?? course.level}</span>
                  </div>
                  <p className="course-card-author">By {course.created_by_name}</p>
                </div>
                <div className="authoring-course-actions">
                  <button
                    className="edit-btn"
                    onClick={() => navigate(`/authoring/courses/${course.id}`)}
                  >
                    <Pencil size={14} /> {course.is_published && course.created_by_id !== user?.id && user?.profile?.user_type !== 'admin' ? 'View' : 'Edit'}
                  </button>
                  <button
                    className="authoring-export-btn"
                    onClick={(e) => { e.stopPropagation(); handleExport(course) }}
                    title="Export as xlsx"
                  >
                    <Download size={14} /> Export
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
