import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import client from '../api/client'
import './HomePage.css'

ContinueLearningBanner.propTypes = {
  data: PropTypes.shape({
    course_id: PropTypes.number,
    course_title: PropTypes.string,
    current_module_title: PropTypes.string,
    progress_pct: PropTypes.number,
  }),
}

function ContinueLearningBanner({ data }) {
  const navigate = useNavigate()
  if (!data) return null
  return (
    <div className="continue-banner">
      <p className="continue-label">Continue Learning</p>
      <h2>{data.course_title}</h2>
      {data.current_module_title && (
        <p className="current-module">Current: {data.current_module_title}</p>
      )}
      <div className="progress-row">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${data.progress_pct}%` }} />
        </div>
        <span className="progress-pct">{data.progress_pct}% complete</span>
      </div>
      <button
        className="resume-btn"
        onClick={() => navigate(`/courses/${data.course_id}/learn`)}
      >
        Resume
      </button>
    </div>
  )
}

PillarCard.propTypes = {
  pillar: PropTypes.shape({
    name: PropTypes.string,
    description: PropTypes.string,
    progress_pct: PropTypes.number,
    course_count: PropTypes.number,
    slug: PropTypes.string,
  }),
}

function PillarCard({ pillar }) {
  return (
    <div className="pillar-card">
      <h3>{pillar.name}</h3>
      <p className="pillar-desc">{pillar.description}</p>
      <div className="pillar-progress">
        <span>Overall Progress</span>
        <span className="pillar-pct">{pillar.progress_pct}%</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill dark" style={{ width: `${pillar.progress_pct}%` }} />
      </div>
      <div className="pillar-footer">
        <span>{pillar.course_count} courses</span>
        <a href={`/courses?pillar=${pillar.slug}`}>View courses →</a>
      </div>
    </div>
  )
}

export default function HomePage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/home/')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load dashboard.'))
  }, [])

  if (error) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">Loading…</p>

  return (
    <div className="home-page">
      <ContinueLearningBanner data={data.continue_learning} />
      <section className="pillars-section">
        <h2>AI Learning Pillars</h2>
        <div className="pillars-grid">
          {data.pillars.map((pillar) => (
            <PillarCard key={pillar.id} pillar={pillar} />
          ))}
        </div>
      </section>
    </div>
  )
}
