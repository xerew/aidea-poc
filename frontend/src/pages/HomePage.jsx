import { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
  return (
    <div className="pillar-card">
      <h3>{pillar.name}</h3>
      <p className="pillar-desc">{pillar.description}</p>
      <div className="pillar-progress">
        <span>{t('common.overallProgress')}</span>
        <span className="pillar-pct">{pillar.progress_pct}%</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill dark" style={{ width: `${pillar.progress_pct}%` }} />
      </div>
      <div className="pillar-footer">
        <span>{t('home.courseCount', { count: pillar.course_count })}</span>
        <a href={`/courses?pillar=${pillar.slug}`}>{t('home.viewCourses')}</a>
      </div>
    </div>
  )
}

RecCard.propTypes = {
  rec: PropTypes.shape({
    course_id: PropTypes.number,
    title: PropTypes.string,
    pillar_name: PropTypes.string,
    reason: PropTypes.string,
    source: PropTypes.string,
  }),
  rank: PropTypes.number,
  onFireEvent: PropTypes.func,
}

function RecCard({ rec, rank, onFireEvent }) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleClick = (e) => {
    e.preventDefault()
    onFireEvent('clicked', rec.course_id, rank, rec.source)
    navigate(`/courses/${rec.course_id}`, {
      state: { fromRec: true, recRank: rank, recSource: rec.source },
    })
  }

  return (
    <div className="rec-card">
      <span className="rec-pillar">{rec.pillar_name}</span>
      <h3 className="rec-title">{rec.title}</h3>
      <p className="rec-reason">{rec.reason}</p>
      <a href={`/courses/${rec.course_id}`} className="rec-link" onClick={handleClick}>
        {t('home.startCourse')}
      </a>
    </div>
  )
}

CfRecCard.propTypes = {
  rec: PropTypes.shape({
    course_id: PropTypes.number,
    title: PropTypes.string,
    reason: PropTypes.string,
    source: PropTypes.string,
  }),
  rank: PropTypes.number,
  onFireEvent: PropTypes.func,
}

function CfRecCard({ rec, rank, onFireEvent }) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleClick = (e) => {
    e.preventDefault()
    onFireEvent('clicked', rec.course_id, rank, rec.source)
    navigate(`/courses/${rec.course_id}`, {
      state: { fromRec: true, recRank: rank, recSource: rec.source },
    })
  }

  return (
    <div className="rec-card cf-card">
      <h3 className="rec-title">{rec.title}</h3>
      <p className="rec-reason cf-reason">{rec.reason}</p>
      <a href={`/courses/${rec.course_id}`} className="rec-link" onClick={handleClick}>
        {t('home.viewCourseArrow')}
      </a>
    </div>
  )
}

export default function HomePage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [data, setData]             = useState(null)
  const [error, setError]           = useState('')
  const [personalRecs, setPersonal] = useState([])
  const [cfRecs, setCf]             = useState([])
  const [recsLoading, setRecsLoading] = useState(false)

  useEffect(() => {
    client.get('/home/')
      .then((res) => setData(res.data))
      .catch(() => setError(t('home.loadError')))
  }, [t])

  const fireEvent = useCallback((eventType, courseId, rank, source) => {
    client.post('/recommendations/events/', {
      course_id: courseId,
      event_type: eventType,
      rank,
      source,
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!user?.profile?.onboarding_completed) return
    let cancelled = false

    const fetchRecs = async () => {
      setRecsLoading(true)
      try {
        const res = await client.get('/recommendations/')
        if (cancelled) return
        const all = res.data
        const personal = all.filter((r) => r.source === 'personal')
        const cf       = all.filter((r) => r.source === 'cf')
        setPersonal(personal)
        setCf(cf)
        personal.forEach((r, i) => fireEvent('shown', r.course_id, i + 1, 'personal'))
        cf.forEach((r, i)       => fireEvent('shown', r.course_id, i + 1, 'cf'))
      } catch {
        // silently ignore
      } finally {
        if (!cancelled) setRecsLoading(false)
      }
    }

    fetchRecs()
    return () => { cancelled = true }
  }, [user, fireEvent])

  if (error) return <p className="page-error">{error}</p>
  if (!data)  return <p className="page-loading">{t('common.loading')}</p>

  const showRecs = user?.profile?.onboarding_completed

  return (
    <div className="home-page">
      <ContinueLearningBanner data={data.continue_learning} />

      <section className="pillars-section">
        <h2>{t('home.pillarsTitle')}</h2>
        <div className="pillars-grid">
          {data.pillars.map((pillar) => (
            <PillarCard key={pillar.id} pillar={pillar} />
          ))}
        </div>
      </section>

      {showRecs && (recsLoading || personalRecs.length > 0) && (
        <section className="recommendations-section">
          <h2 className="recommendations-title">{t('home.recommendedTitle')}</h2>
          {recsLoading ? (
            <div className="recommendations-grid">
              {[1, 2, 3].map((i) => <div key={i} className="rec-card rec-card-skeleton" />)}
            </div>
          ) : (
            <div className="recommendations-grid">
              {personalRecs.map((rec, i) => (
                <RecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
              ))}
            </div>
          )}
        </section>
      )}

      {showRecs && cfRecs.length > 0 && (
        <section className="recommendations-section cf-section">
          <h2 className="recommendations-title cf-title">{t('home.cfTitle')}</h2>
          <div className="cf-grid">
            {cfRecs.map((rec, i) => (
              <CfRecCard key={rec.course_id} rec={rec} rank={i + 1} onFireEvent={fireEvent} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
