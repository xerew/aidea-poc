import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Clock, BookOpen, CheckCircle2, Circle } from 'lucide-react'
import client from '../api/client'
import './CourseDetailPage.css'

const PILLAR_STYLES = {
  'teach-with-ai':  { color: 'blue' },
  'teach-for-ai':   { color: 'purple' },
  'teach-about-ai': { color: 'green' },
}

const LEVEL_LABELS = {
  beginner:     'Beginner',
  intermediate: 'Intermediate',
  advanced:     'Advanced',
}

export default function CourseDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const recMeta = location.state
  const [course, setCourse] = useState(null)
  const [enrolling, setEnrolling] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get(`/courses/${id}/`)
      .then((res) => setCourse(res.data))
      .catch(() => setError('Failed to load course.'))
  }, [id])

  const handleEnroll = async () => {
    setEnrolling(true)
    try {
      await client.post(`/courses/${id}/enroll/`)
      const res = await client.get(`/courses/${id}/`)
      setCourse(res.data)
      if (recMeta?.fromRec) {
        client.post('/recommendations/events/', {
          course_id: Number(id),
          event_type: 'enrolled',
          rank: recMeta.recRank ?? 0,
          source: recMeta.recSource ?? 'personal',
        }).catch(() => {})
      }
    } catch {
      setError('Enrollment failed.')
    } finally {
      setEnrolling(false)
    }
  }

  if (error)   return <p className="page-error">{error}</p>
  if (!course) return <p className="page-loading">Loading…</p>

  const pillarStyle = PILLAR_STYLES[course.pillar.slug] ?? { color: 'blue' }

  return (
    <div className="course-detail">

      {/* Back */}
      <button className="back-link" onClick={() => navigate('/courses')}>
        <ArrowLeft size={15} /> Back to Courses
      </button>

      {/* Hero */}
      <div className="detail-hero">
        <div className="detail-hero-meta">
          <span className={`pillar-badge pillar-badge--${pillarStyle.color}`}>
            {course.pillar.name}
          </span>
          <span className="level-label">{LEVEL_LABELS[course.level] ?? course.level}</span>
        </div>

        {!course.is_enrolled && (
          <button className="enroll-btn" onClick={handleEnroll} disabled={enrolling}>
            {enrolling ? 'Enrolling…' : 'Enroll Now'}
          </button>
        )}
        {course.is_enrolled && (
          <button
            className="enroll-btn enroll-btn--continue"
            onClick={() => navigate(`/courses/${id}/learn`)}
          >
            Continue
          </button>
        )}
      </div>

      <h1 className="detail-title">{course.title}</h1>
      <p className="detail-desc">{course.description}</p>

      <div className="detail-stats">
        <span><Clock size={15} /> {course.duration_hours} hours</span>
        <span><BookOpen size={15} /> {course.module_count} modules</span>
      </div>

      {/* Enrolled progress */}
      {course.is_enrolled && (
        <div className="detail-progress">
          <div className="progress-row">
            <span>Your progress</span>
            <span>{course.progress_pct}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${course.progress_pct}%` }} />
          </div>
        </div>
      )}

      {/* What You'll Learn */}
      {course.learning_outcomes?.length > 0 && (
        <div className="outcomes-card">
          <h2>What You&apos;ll Learn</h2>
          <div className="outcomes-grid">
            {course.learning_outcomes.map((outcome, i) => (
              <div key={i} className="outcome-item">
                <CheckCircle2 size={18} className="outcome-icon" />
                <span>{outcome}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modules */}
      <section className="modules-section">
        <h2>Course Modules</h2>
        <div className="modules-list">
          {course.modules.map((mod) => {
            const isCurrent = mod.id === course.current_module_id
            return (
              <div key={mod.id} className={`module-row ${isCurrent ? 'module-row--current' : ''}`}>
                <div className="module-number">{mod.order}</div>
                <div className="module-body">
                  <p className="module-title">Module {mod.order} — {mod.title}</p>
                  {mod.description && <p className="module-desc">{mod.description}</p>}
                  <p className="module-meta">
                    {mod.duration_minutes > 0 && <span>{mod.duration_minutes} min</span>}
                  </p>
                </div>
                <div className="module-status">
                  {isCurrent
                    ? <CheckCircle2 size={22} className="module-status--done" />
                    : <Circle size={22} className="module-status--empty" />
                  }
                </div>
              </div>
            )
          })}
        </div>
      </section>

    </div>
  )
}
