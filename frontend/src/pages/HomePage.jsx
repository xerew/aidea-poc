import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import client from '../api/client'
import ContinueLearningBanner from '../components/ContinueLearningBanner'
import './HomePage.css'

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
