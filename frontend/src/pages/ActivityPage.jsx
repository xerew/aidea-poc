import { useEffect, useState, useCallback, useRef } from 'react'
import PropTypes from 'prop-types'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, CheckCircle2, Circle, Layers } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import ResourceView from '../components/learner/ResourceView'
import TypeIcon from '../components/learner/TypeIcon'
import './ActivityPage.css'

// An activity with a single kind of resource shows that type's icon; a mixed
// activity shows a generic "layers" icon.
ActivityIcon.propTypes = { types: PropTypes.arrayOf(PropTypes.string), size: PropTypes.number }
function ActivityIcon({ types, size = 16 }) {
  if (types?.length === 1) return <TypeIcon type={types[0]} size={size} />
  return <Layers size={size} />
}

// ─── Redirect component (/courses/:id/learn) ─────────────────────────────────

export function LearnRedirect() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return }
    client.get(`/courses/${id}/learn/`)
      .then(res => {
        const activityId = res.data.first_incomplete_lesson_id
        if (activityId) {
          navigate(`/courses/${id}/learn/${activityId}`, { replace: true })
        } else {
          navigate(`/courses/${id}`, { replace: true })
        }
      })
      .catch((err) => setError(
        err.response?.status === 404 ? t('lesson.unavailable') : t('lesson.learnRedirectError'),
      ))
  }, [id, navigate, user, t])

  if (error) return <p className="page-error">{error}</p>
  return <p className="page-loading">{t('common.loading')}</p>
}

// ─── Main ActivityPage ───────────────────────────────────────────────────────

export default function ActivityPage() {
  const { t } = useTranslation()
  const { courseId, lessonId: activityId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [courseLearn, setCourseLearn] = useState(null)
  // The fetched activity, tagged with its id so a stale one is never shown
  // while the next is loading.
  const [loaded, setLoaded] = useState(null)
  const [notes, setNotes] = useState({})
  const [error, setError] = useState('')
  const scrollPctRef = useRef(0)

  const activity = loaded?.id === activityId ? loaded.data : null
  const note = notes[activityId] ?? ''
  const setActivity = useCallback((update) => {
    setLoaded(prev => (prev ? { ...prev, data: update(prev.data) } : prev))
  }, [])

  // Redirect if not logged in
  useEffect(() => {
    if (!user) navigate('/login', { replace: true })
  }, [user, navigate])

  // Fetch sidebar structure whenever courseId changes
  useEffect(() => {
    client.get(`/courses/${courseId}/learn/`)
      .then(res => setCourseLearn(res.data))
      .catch((err) => setError(
        err.response?.status === 404 ? t('lesson.unavailable') : t('lesson.loadCourseError'),
      ))
  }, [courseId, t])

  // Fetch the activity whenever activityId changes
  useEffect(() => {
    scrollPctRef.current = 0
    client.get(`/courses/${courseId}/lessons/${activityId}/`)
      .then(res => setLoaded({ id: activityId, data: res.data }))
      .catch(() => setError(t('lesson.loadLessonError')))
  }, [courseId, activityId, t])

  // Track how far the learner scrolled — sent with text-resource completion
  useEffect(() => {
    const handleScroll = () => {
      const total = document.documentElement.scrollHeight - window.innerHeight
      if (total <= 0) return
      const pct = Math.round((window.scrollY / total) * 100)
      scrollPctRef.current = Math.max(scrollPctRef.current, pct)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const completeResource = useCallback(async (resource, payload = {}) => {
    const body = { ...payload }
    if (resource.type === 'text') body.engagement_data = { scroll_pct: scrollPctRef.current }
    const res = await client.post(
      `/courses/${courseId}/lessons/${activityId}/resources/${resource.id}/complete/`, body,
    )
    const { progress_pct: progressPct, activity_completed: activityDone } = res.data
    // A just-finished quiz keeps its in-session feedback; the stored review
    // (quiz_review) is used when the activity is opened again.
    setActivity(prev => prev && ({
      ...prev,
      is_completed: activityDone,
      resources: prev.resources.map(r => (r.id === resource.id ? { ...r, is_completed: true } : r)),
    }))
    setCourseLearn(prev => prev && ({
      ...prev,
      progress_pct: progressPct,
      modules: prev.modules.map(mod => ({
        ...mod,
        lessons: mod.lessons.map(a => (a.id === Number(activityId) ? { ...a, is_completed: activityDone } : a)),
      })),
    }))
  }, [courseId, activityId, setActivity])

  const handleSubmissionChange = useCallback((resourceId, submission) => {
    setActivity(prev => prev && ({
      ...prev,
      resources: prev.resources.map(r => (r.id === resourceId ? { ...r, submission } : r)),
    }))
  }, [setActivity])

  const goTo = (id) => id && navigate(`/courses/${courseId}/learn/${id}`)

  if (error) return <p className="page-error">{error}</p>

  const resources = activity?.resources ?? []
  const resourceTypes = [...new Set(resources.map(r => r.type))]
  const required = resources.filter(r => r.is_required)
  const doneRequired = required.filter(r => r.is_completed).length

  return (
    <div className="lp-page">

      {/* Top bar */}
      <div className="lp-topbar">
        <button className="lp-back" onClick={() => navigate(`/courses/${courseId}`)}>
          <ArrowLeft size={15} /> {t('lesson.backToCourse')}
        </button>
        <span className="lp-course-title">{courseLearn?.title ?? '…'}</span>
        <div />
      </div>

      <div className="lp-body">

        {/* ── Sidebar ── */}
        <aside className="lp-sidebar">
          {courseLearn?.modules.map(mod => (
            <div key={mod.id} className="lp-sidebar-module">
              <p className="lp-sidebar-module-title">
                {t('common.moduleLabel', { order: mod.order, title: mod.title })}
              </p>
              {mod.lessons.map(act => (
                <button
                  key={act.id}
                  className={`lp-sidebar-lesson ${act.id === Number(activityId) ? 'lp-sidebar-lesson--active' : ''}`}
                  onClick={() => goTo(act.id)}
                >
                  <span className="lp-sidebar-type-icon">
                    <ActivityIcon types={act.resource_types} size={14} />
                  </span>
                  <span className="lp-sidebar-lesson-info">
                    <span className="lp-sidebar-lesson-title">{act.title}</span>
                    {act.duration_minutes > 0 && (
                      <span className="lp-sidebar-lesson-dur">{t('common.minutesLabel', { count: act.duration_minutes })}</span>
                    )}
                  </span>
                  {act.is_completed
                    ? <CheckCircle2 size={18} className="lp-check-done" />
                    : <Circle size={18} className="lp-check-empty" />
                  }
                </button>
              ))}
            </div>
          ))}

          {courseLearn && (
            <div className="lp-sidebar-progress">
              <div className="lp-sidebar-progress-row">
                <span>{t('common.progress')}</span>
                <span>{courseLearn.progress_pct}%</span>
              </div>
              <div className="lp-sidebar-progress-bar">
                <div
                  className="lp-sidebar-progress-fill"
                  style={{ width: `${courseLearn.progress_pct}%` }}
                />
              </div>
            </div>
          )}
        </aside>

        {/* ── Main ── */}
        <main className="lp-main">
          {!activity ? (
            <p className="page-loading">{t('lesson.loadingLesson')}</p>
          ) : (
            <>
              {/* Activity header */}
              <div className="lp-lesson-header">
                <span className="lp-type-tag">
                  <ActivityIcon types={resourceTypes} size={14} />
                  {resourceTypes.length === 1
                    ? t(`lesson.type.${resourceTypes[0]}`)
                    : t('lesson.activity')}
                  {required.length > 1 && (
                    <span className="lp-resource-count">
                      · {t('lesson.resource.progress', { done: doneRequired, total: required.length })}
                    </span>
                  )}
                </span>
                <h1 className="lp-lesson-title">{activity.title}</h1>
                {activity.description && (
                  <p className="lp-lesson-desc">{activity.description}</p>
                )}
              </div>

              {/* Resources, in order */}
              {resources.length === 0 ? (
                <div className="lp-content-card"><p className="lp-empty">{t('lesson.noContent')}</p></div>
              ) : resources.map(resource => (
                <ResourceView
                  key={resource.id}
                  resource={resource}
                  courseId={courseId}
                  activityId={activityId}
                  onComplete={completeResource}
                  onSubmissionChange={handleSubmissionChange}
                />
              ))}

              {/* Navigation */}
              <div className="lp-nav">
                <button
                  className="lp-nav-btn"
                  disabled={!activity.prev_lesson_id}
                  onClick={() => goTo(activity.prev_lesson_id)}
                >
                  &#8249; {t('common.previous')}
                </button>

                {activity.is_completed && (
                  <span className="lp-complete-btn lp-complete-btn--done">{t('lesson.activityComplete')}</span>
                )}

                <button
                  className="lp-nav-btn lp-nav-btn--primary"
                  disabled={!activity.next_lesson_id}
                  onClick={() => goTo(activity.next_lesson_id)}
                >
                  {t('common.next')} &#8250;
                </button>
              </div>

              {/* Notes */}
              <div className="lp-notes">
                <h3 className="lp-notes-title">{t('lesson.yourNotesTitle')}</h3>
                <textarea
                  className="lp-notes-input"
                  placeholder={t('lesson.notesPlaceholder')}
                  value={note}
                  onChange={e => setNotes(prev => ({ ...prev, [activityId]: e.target.value }))}
                />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
