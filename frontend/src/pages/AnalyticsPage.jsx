import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { Users, CheckCircle, Target, Award } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './AnalyticsPage.css'

const STAT_CARDS = [
  { key: 'total_enrollments', label: 'Total Enrollments', Icon: Users,       color: 'blue'   },
  { key: 'completion_rate',   label: 'Completion Rate',   Icon: CheckCircle, color: 'green'  },
  { key: 'quiz_attempts',     label: 'Quiz Attempts',     Icon: Target,      color: 'purple' },
  { key: 'courses_created',   label: 'Courses Created',   Icon: Award,       color: 'orange' },
]

StatCard.propTypes = {
  stat: PropTypes.shape({
    key: PropTypes.string,
    label: PropTypes.string,
    Icon: PropTypes.elementType,
    color: PropTypes.string,
  }),
  value: PropTypes.number,
}

function StatCard({ stat, value }) {
  const { Icon, label, color } = stat
  const display = stat.key === 'completion_rate' ? `${value}%` : value
  return (
    <div className="an-stat-card">
      <div className={`an-stat-icon an-stat-icon--${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="an-stat-value">{display}</p>
        <p className="an-stat-label">{label}</p>
      </div>
    </div>
  )
}

CourseRow.propTypes = {
  course: PropTypes.shape({
    title: PropTypes.string,
    enrolled: PropTypes.number,
    completed: PropTypes.number,
    in_progress: PropTypes.number,
    completion_rate: PropTypes.number,
    avg_time_minutes: PropTypes.number,
  }),
}

function CourseRow({ course }) {
  return (
    <div className="an-course-row">
      <div className="an-course-header">
        <span className="an-course-title">{course.title}</span>
        <span className="an-course-pct">{course.completion_rate}% completed</span>
      </div>
      <div className="an-course-stats">
        <div className="an-course-stat an-course-stat--blue">
          <span className="an-course-stat-value">{course.enrolled}</span>
          <span className="an-course-stat-label">Enrolled</span>
        </div>
        <div className="an-course-stat an-course-stat--green">
          <span className="an-course-stat-value">{course.completed}</span>
          <span className="an-course-stat-label">Completed</span>
        </div>
        <div className="an-course-stat an-course-stat--orange">
          <span className="an-course-stat-value">{course.in_progress}</span>
          <span className="an-course-stat-label">In Progress</span>
        </div>
        <div className="an-course-stat an-course-stat--purple">
          <span className="an-course-stat-value">{course.avg_time_minutes}m</span>
          <span className="an-course-stat-label">Avg. Time</span>
        </div>
      </div>
      <div className="an-course-bar-track">
        <div className="an-course-bar-fill" style={{ width: `${course.completion_rate}%` }} />
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const isCreator = user?.profile?.user_type === 'content_creator'

  useEffect(() => {
    if (!isCreator) return
    client.get('/analytics/overview/')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load analytics.'))
  }, [isCreator])

  if (!isCreator) {
    return (
      <div className="an-restricted">
        <p>Content Analytics is only available to content creators.</p>
      </div>
    )
  }

  if (error) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">Loading&hellip;</p>

  return (
    <div className="analytics-page">
      <p className="an-subtitle">Track engagement and performance across your created courses</p>

      <div className="an-stat-grid">
        {STAT_CARDS.map((stat) => (
          <StatCard key={stat.key} stat={stat} value={data.summary[stat.key]} />
        ))}
      </div>

      <section className="an-section">
        <h2 className="an-section-title">Course Completion Overview</h2>
        <div className="an-course-list">
          {data.courses.length === 0 ? (
            <p className="an-empty">No courses created by you yet. Courses you create in Authoring will appear here — including drafts.</p>
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
