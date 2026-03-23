import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Clock } from 'lucide-react'
import client from '../api/client'
import ContinueLearningBanner from '../components/ContinueLearningBanner'
import './MyLearningPage.css'

function timeAgo(dateStr) {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} day${days !== 1 ? 's' : ''} ago`
  const months = Math.floor(days / 30)
  return `${months} month${months !== 1 ? 's' : ''} ago`
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

InProgressCard.propTypes = {
  enrollment: PropTypes.shape({
    course_id: PropTypes.number,
    course_title: PropTypes.string,
    pillar_name: PropTypes.string,
    progress_pct: PropTypes.number,
    module_count: PropTypes.number,
    last_accessed_at: PropTypes.string,
  }),
}

function InProgressCard({ enrollment }) {
  const navigate = useNavigate()
  return (
    <div className="ml-card ml-card--progress">
      <div className="ml-card-top-row">
        <div className="ml-card-main">
          <div className="ml-card-header">
            <span className="ml-pillar-badge">{enrollment.pillar_name}</span>
            <span className="ml-card-title">{enrollment.course_title}</span>
          </div>
          <div className="ml-card-meta">
            <span className="ml-meta-item">
              <Clock size={12} />
              Last activity: {timeAgo(enrollment.last_accessed_at)}
            </span>
            <span className="ml-meta-sep">·</span>
            <span className="ml-meta-item">{enrollment.module_count} module{enrollment.module_count !== 1 ? 's' : ''}</span>
          </div>
        </div>
        <button
          className="ml-action-btn"
          onClick={() => navigate(`/courses/${enrollment.course_id}/learn`)}
        >
          Resume
        </button>
      </div>
      <div className="ml-progress-track">
        <div className="ml-progress-bar ml-progress-bar--card">
          <div className="ml-progress-fill" style={{ width: `${enrollment.progress_pct}%` }} />
        </div>
        <span className="ml-card-pct">{enrollment.progress_pct}% complete</span>
      </div>
    </div>
  )
}

CompletedCard.propTypes = {
  enrollment: PropTypes.shape({
    course_id: PropTypes.number,
    course_title: PropTypes.string,
    pillar_name: PropTypes.string,
    last_accessed_at: PropTypes.string,
  }),
}

function CompletedCard({ enrollment }) {
  const navigate = useNavigate()
  return (
    <div className="ml-card ml-card--completed">
      <div className="ml-card-top">
        <span className="ml-pillar-badge">{enrollment.pillar_name}</span>
        <span className="ml-completed-badge">&#x2713; Completed</span>
      </div>
      <h3 className="ml-card-title ml-card-title--completed">{enrollment.course_title}</h3>
      <p className="ml-completed-date">Completed on {formatDate(enrollment.last_accessed_at)}</p>
      <button
        className="ml-review-btn"
        onClick={() => navigate(`/courses/${enrollment.course_id}/learn`)}
      >
        Review Course
      </button>
    </div>
  )
}

export default function MyLearningPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/my-learning/')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load your learning data.'))
  }, [])

  if (error) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">Loading&hellip;</p>

  const { continue_learning, in_progress, completed } = data
  const hasAny = in_progress.length > 0 || completed.length > 0

  return (
    <div className="my-learning-page">
      <p className="ml-subtitle">Track your progress and continue your courses</p>

      <ContinueLearningBanner data={continue_learning} />

      {!hasAny && (
        <div className="ml-empty">
          <p>You haven&apos;t enrolled in any courses yet.</p>
          <a href="/courses">Browse courses</a>
        </div>
      )}

      {in_progress.length > 0 && (
        <section className="ml-section">
          <h2 className="ml-section-title">In Progress</h2>
          <div className="ml-cards-list">
            {in_progress.map((e) => (
              <InProgressCard key={e.course_id} enrollment={e} />
            ))}
          </div>
        </section>
      )}

      {completed.length > 0 && (
        <section className="ml-section">
          <h2 className="ml-section-title">Completed</h2>
          <div className="ml-cards-grid">
            {completed.map((e) => (
              <CompletedCard key={e.course_id} enrollment={e} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
