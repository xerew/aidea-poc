import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import client from '../api/client'
import ContinueLearningBanner from '../components/ContinueLearningBanner'
import { useAuth } from '../context/AuthContext'
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
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [recommendations, setRecommendations] = useState([])
  const [recsLoading, setRecsLoading] = useState(false)

  useEffect(() => {
    client.get('/home/')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load dashboard.'))
  }, [])

  useEffect(() => {
    if (!user?.profile?.onboarding_completed) return
    let cancelled = false
    const fetchRecs = async () => {
      setRecsLoading(true)
      try {
        const res = await client.get('/recommendations/')
        if (!cancelled) setRecommendations(res.data)
      } catch {
        // silently ignore recommendation errors
      } finally {
        if (!cancelled) setRecsLoading(false)
      }
    }
    fetchRecs()
    return () => { cancelled = true }
  }, [user])

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

      {user?.profile?.onboarding_completed && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">Recommended for you</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map(i => (
                <div key={i} className="rec-card rec-card-skeleton" />
              ))}
            </div>
          ) : recommendations.length > 0 ? (
            <div className="recommendations-grid">
              {recommendations.map(rec => (
                <div key={rec.course_id} className="rec-card">
                  <span className="rec-pillar">{rec.pillar_name}</span>
                  <h3 className="rec-title">{rec.title}</h3>
                  <p className="rec-reason">{rec.reason}</p>
                  <a href={`/courses/${rec.course_id}`} className="rec-link">
                    Start course →
                  </a>
                </div>
              ))}
            </div>
          ) : null}
        </section>
      )}
    </div>
  )
}
