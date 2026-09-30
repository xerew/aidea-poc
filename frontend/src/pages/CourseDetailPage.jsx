import { useEffect, useState } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { ArrowLeft, Clock, BookOpen, CheckCircle2, Circle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { subjectLabel } from '../lib/subjects'
import './CourseDetailPage.css'

const PILLAR_STYLES = {
  'teach-with-ai':  { color: 'blue' },
  'teach-for-ai':   { color: 'purple' },
  'teach-about-ai': { color: 'green' },
}

export default function CourseDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const recMeta = location.state
  const [course, setCourse] = useState(null)
  const [enrolling, setEnrolling] = useState(false)
  const [error, setError] = useState('')

  const levelLabels = {
    beginner: t('common.level.beginner'),
    intermediate: t('common.level.intermediate'),
    advanced: t('common.level.advanced'),
  }

  useEffect(() => {
    client.get(`/courses/${id}/`)
      .then((res) => setCourse(res.data))
      .catch((err) => setError(
        // The catalog only serves published courses, so a 404 here means the
        // course was unpublished rather than a real load failure.
        err.response?.status === 404
          ? t('courseDetail.unavailable')
          : t('courseDetail.loadError'),
      ))
  }, [id, t])

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
      setError(t('courseDetail.enrollError'))
    } finally {
      setEnrolling(false)
    }
  }

  if (error)   return <p className="page-error">{error}</p>
  if (!course) return <p className="page-loading">{t('common.loading')}</p>

  const pillarStyle = PILLAR_STYLES[course.pillar.slug] ?? { color: 'blue' }
  const joinWithOther = (values, prefix, other) => [
    ...(values ?? []).map((v) => t(`authoring.proposal.${prefix}.${v}`)),
    ...(other ? [other] : []),
  ].join(', ')
  const audience = joinWithOther(course.target_audience, 'audience', course.target_audience_other)
  const levels = joinWithOther(course.educational_levels, 'level', course.educational_level_other)
  const profileRows = [
    [t('authoring.proposal.targetAudience'), audience],
    [t('authoring.proposal.educationalLevel'), levels],
    [t('authoring.proposal.priorKnowledge'), course.prior_knowledge],
    [t('authoring.proposal.crossAxis'), course.cross_axis_relevance],
  ].filter(([, value]) => value)

  return (
    <div className="course-detail">

      {/* Back */}
      <button className="back-link" onClick={() => navigate('/courses')}>
        <ArrowLeft size={15} /> {t('courseDetail.backToCourses')}
      </button>

      {/* Hero */}
      <div className="detail-hero">
        <div className="detail-hero-meta">
          <span className={`pillar-badge pillar-badge--${pillarStyle.color}`}>
            {course.pillar.name}
          </span>
          {(course.additional_pillars ?? []).map((p) => (
            <span
              key={p.id}
              className={`pillar-badge pillar-badge--outline pillar-badge--${(PILLAR_STYLES[p.slug] ?? { color: 'blue' }).color}`}
              title={t('courseDetail.alsoRelevantTo')}
            >
              {p.name}
            </span>
          ))}
          <span className="level-label">{levelLabels[course.level] ?? course.level}</span>
        </div>

        {!course.is_enrolled && (
          <button className="enroll-btn" onClick={handleEnroll} disabled={enrolling}>
            {enrolling ? t('courseDetail.enrolling') : t('courseDetail.enrollNow')}
          </button>
        )}
        {course.is_enrolled && (
          <button
            className="enroll-btn enroll-btn--continue"
            onClick={() => navigate(`/courses/${id}/learn`)}
          >
            {t('common.continue')}
          </button>
        )}
      </div>

      <h1 className="detail-title">{course.title}</h1>
      {course.created_by_id && (
        <p className="detail-author">
          {t('courseDetail.by')}{' '}
          <Link to={`/users/${course.created_by_id}`}>{course.created_by_name}</Link>
        </p>
      )}
      <p className="detail-desc">{course.description}</p>

      {course.subjects?.length > 0 && (
        <div className="detail-subjects">
          {course.subjects.map((s) => (
            <span key={s.id} className="subject-tag">{subjectLabel(s, t)}</span>
          ))}
        </div>
      )}

      <div className="detail-stats">
        <span><Clock size={15} /> {t('common.durationHours', { count: course.duration_hours })}</span>
        <span><BookOpen size={15} /> {t('common.moduleCount', { count: course.module_count })}</span>
      </div>

      {/* Enrolled progress */}
      {course.is_enrolled && (
        <div className="detail-progress">
          <div className="progress-row">
            <span>{t('courseDetail.yourProgress')}</span>
            <span>{course.progress_pct}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${course.progress_pct}%` }} />
          </div>
        </div>
      )}

      {/* Course profile: audience, level, prior knowledge, cross-axis relevance */}
      {profileRows.length > 0 && (
        <div className="outcomes-card">
          <h2>{t('authoring.proposal.title')}</h2>
          <dl className="course-profile">
            {profileRows.map(([label, value]) => (
              <div key={label} className="course-profile-row">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* What You'll Learn */}
      {course.learning_outcomes?.length > 0 && (
        <div className="outcomes-card">
          <h2>{t('courseDetail.whatYoullLearn')}</h2>
          <div className="outcomes-grid">
            {course.learning_outcomes.map((outcome, i) => (
              <div key={i} className="outcome-item">
                <CheckCircle2 size={18} className="outcome-icon" />
                <span><span className="outcome-num">{i + 1}.</span> {outcome}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modules */}
      <section className="modules-section">
        <h2>{t('courseDetail.courseModules')}</h2>
        <div className="modules-list">
          {course.modules.map((mod) => {
            const isCompleted = course.completed_module_ids?.includes(mod.id)
            const isCurrent = mod.id === course.current_module_id
            return (
              <div key={mod.id} className={`module-row ${isCurrent ? 'module-row--current' : ''}`}>
                <div className="module-number">{mod.order}</div>
                <div className="module-body">
                  <p className="module-title">{t('common.moduleLabel', { order: mod.order, title: mod.title })}</p>
                  {mod.description && <p className="module-desc">{mod.description}</p>}
                  <p className="module-meta">
                    {mod.duration_minutes > 0 && <span>{t('common.minutesLabel', { count: mod.duration_minutes })}</span>}
                  </p>
                  {(mod.related_outcomes ?? []).some((i) => course.learning_outcomes?.[i]) && (
                    <p className="module-outcome-links">
                      {t('courseDetail.coversOutcomes')}{' '}
                      {mod.related_outcomes.filter((i) => course.learning_outcomes?.[i]).map((i) => (
                        <span key={i} className="module-outcome-ref" title={course.learning_outcomes[i]}>
                          {i + 1}
                        </span>
                      ))}
                    </p>
                  )}
                </div>
                <div className="module-status">
                  {isCompleted
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
