import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Users, CheckCircle, Target, Award, Download, ChevronDown, ChevronRight, Clock } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './AnalyticsPage.css'

const STAT_CARDS = [
  { key: 'total_enrollments', labelKey: 'analytics.stats.totalEnrollments', Icon: Users,       color: 'blue'   },
  { key: 'completion_rate',   labelKey: 'analytics.stats.completionRate',   Icon: CheckCircle, color: 'green'  },
  { key: 'quiz_attempts',     labelKey: 'analytics.stats.quizAttempts',     Icon: Target,      color: 'purple' },
  { key: 'courses_created',   labelKey: 'analytics.stats.coursesCreated',   Icon: Award,       color: 'orange' },
]

StatCard.propTypes = {
  stat: PropTypes.shape({
    key: PropTypes.string,
    labelKey: PropTypes.string,
    Icon: PropTypes.elementType,
    color: PropTypes.string,
  }),
  value: PropTypes.number,
}

function StatCard({ stat, value }) {
  const { t } = useTranslation()
  const { Icon, labelKey, color } = stat
  const display = stat.key === 'completion_rate' ? `${value}%` : value
  return (
    <div className="an-stat-card">
      <div className={`an-stat-icon an-stat-icon--${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="an-stat-value">{display}</p>
        <p className="an-stat-label">{t(labelKey)}</p>
      </div>
    </div>
  )
}

// ── Per-teacher drill-down (#27) ──────────────────────────────────────────────

TeacherDetail.propTypes = { teacher: PropTypes.object.isRequired }

function TeacherDetail({ teacher }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const minutes = Math.round((teacher.time_spent_seconds || 0) / 60)
  const hasQuizzes = teacher.quizzes.length > 0

  return (
    <div className="an-teacher">
      <button className="an-teacher-head" onClick={() => hasQuizzes && setOpen(o => !o)}>
        {hasQuizzes ? (open ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span className="an-teacher-spacer" />}
        <span className="an-teacher-name">{teacher.name}</span>
        <span className="an-teacher-meta">
          {t('analytics.pctCompleted', { pct: teacher.progress_pct })}
          <span className="an-teacher-dot">·</span>
          <Clock size={12} /> {t('analytics.minutes', { count: minutes })}
          {teacher.avg_quiz_score != null && (
            <>
              <span className="an-teacher-dot">·</span>
              {t('analytics.avgScore', { pct: Math.round(teacher.avg_quiz_score * 100) })}
            </>
          )}
        </span>
      </button>

      {open && teacher.quizzes.map(quiz => (
        <div key={quiz.lesson_id} className="an-quiz">
          <p className="an-quiz-title">
            {quiz.lesson_title}
            {quiz.score != null && ` — ${Math.round(quiz.score * 100)}%`}
          </p>
          {quiz.questions.map((q, i) => (
            <div key={i} className={`an-answer ${q.is_correct ? 'an-answer--ok' : 'an-answer--bad'}`}>
              <span className="an-answer-q">{q.question}</span>
              <span className="an-answer-a">
                {q.selected_text
                  ? t('analytics.chose', { answer: q.selected_text })
                  : t('analytics.notAnswered')}
                {!q.is_correct && q.correct_text && ` · ${t('analytics.correctAnswer', { answer: q.correct_text })}`}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

CourseRow.propTypes = {
  course: PropTypes.shape({
    id: PropTypes.number,
    title: PropTypes.string,
    enrolled: PropTypes.number,
    completed: PropTypes.number,
    in_progress: PropTypes.number,
    completion_rate: PropTypes.number,
    avg_time_minutes: PropTypes.number,
    owned: PropTypes.bool,
  }),
}

function CourseRow({ course }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const [teachers, setTeachers] = useState(null)
  const [loadingTeachers, setLoadingTeachers] = useState(false)

  const toggle = () => {
    const next = !expanded
    setExpanded(next)
    if (next && teachers === null && !loadingTeachers) {
      setLoadingTeachers(true)
      client.get(`/analytics/courses/${course.id}/teachers/`)
        .then(res => setTeachers(res.data.teachers))
        .catch(() => setTeachers([]))
        .finally(() => setLoadingTeachers(false))
    }
  }

  return (
    <div className="an-course-row">
      <div className="an-course-header">
        <span className="an-course-title">{course.title}</span>
        <span className="an-course-pct">{t('analytics.pctCompleted', { pct: course.completion_rate })}</span>
      </div>
      <div className="an-course-stats">
        <div className="an-course-stat an-course-stat--blue">
          <span className="an-course-stat-value">{course.enrolled}</span>
          <span className="an-course-stat-label">{t('analytics.enrolled')}</span>
        </div>
        <div className="an-course-stat an-course-stat--green">
          <span className="an-course-stat-value">{course.completed}</span>
          <span className="an-course-stat-label">{t('analytics.completed')}</span>
        </div>
        <div className="an-course-stat an-course-stat--orange">
          <span className="an-course-stat-value">{course.in_progress}</span>
          <span className="an-course-stat-label">{t('analytics.inProgress')}</span>
        </div>
        <div className="an-course-stat an-course-stat--purple">
          <span className="an-course-stat-value">{t('analytics.avgTimeValue', { minutes: course.avg_time_minutes })}</span>
          <span className="an-course-stat-label">{t('analytics.avgTime')}</span>
        </div>
      </div>
      <div className="an-course-bar-track">
        <div className="an-course-bar-fill" style={{ width: `${course.completion_rate}%` }} />
      </div>

      {course.owned && (
        <>
          <button className="an-teachers-toggle" onClick={toggle}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            {expanded ? t('analytics.hideTeachers') : t('analytics.viewTeachers')}
          </button>
          {expanded && (
            <div className="an-teachers">
              {loadingTeachers && <p className="an-teachers-loading">{t('common.loading')}</p>}
              {teachers && teachers.length === 0 && <p className="an-teachers-loading">{t('analytics.noTeachers')}</p>}
              {teachers && teachers.map(tt => <TeacherDetail key={tt.user_id} teacher={tt} />)}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function AnalyticsPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const isCreator = user?.profile?.user_type === 'content_creator'

  useEffect(() => {
    if (!isCreator) return
    client.get('/analytics/overview/')
      .then((res) => setData(res.data))
      .catch(() => setError(t('analytics.loadError')))
  }, [isCreator, t])

  if (!isCreator) {
    return (
      <div className="an-restricted">
        <p>{t('analytics.restricted')}</p>
      </div>
    )
  }

  const handleExport = async () => {
    try {
      const res = await client.get('/analytics/export/', { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'analytics.xlsx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch { /* ignore */ }
  }

  if (error) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">{t('common.loading')}</p>

  return (
    <div className="analytics-page">
      <div className="an-header-row">
        <p className="an-subtitle">{t('analytics.subtitle')}</p>
        <button className="an-export-btn" onClick={handleExport}>
          <Download size={15} /> {t('analytics.downloadExcel')}
        </button>
      </div>

      <div className="an-stat-grid">
        {STAT_CARDS.map((stat) => (
          <StatCard key={stat.key} stat={stat} value={data.summary[stat.key]} />
        ))}
      </div>

      <section className="an-section">
        <h2 className="an-section-title">{t('analytics.courseCompletionOverview')}</h2>
        <div className="an-course-list">
          {data.courses.length === 0 ? (
            <p className="an-empty">{t('analytics.empty')}</p>
          ) : (
            data.courses.map((course) => (
              <CourseRow key={course.id} course={course} />
            ))
          )}
        </div>
      </section>
    </div>
  )
}
