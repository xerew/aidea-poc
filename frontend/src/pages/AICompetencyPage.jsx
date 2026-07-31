import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './AICompetencyPage.css'

const LIKERT = [1, 2, 3, 4, 5]
const LIKERT_KEYS = ['stronglyDisagree', 'disagree', 'neither', 'agree', 'stronglyAgree']
// Overall band → 0-6 competency_score, mirroring the backend mapping.
const BAND_TO_SCORE = { low: 1, moderate: 3, high: 5 }

export default function AICompetencyPage() {
  const { t, i18n } = useTranslation()
  // Localize backend content (dimension names, questions) to the active UI
  // language, which can be ahead of the stored profile language after register.
  const lang = i18n.language?.split('-')[0]
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [data, setData]       = useState(null)
  const [answers, setAnswers] = useState({})   // { "<qid>": 1-5 }
  const [saving, setSaving]   = useState(false)
  const [editing, setEditing] = useState(false) // in the questionnaire (retake in progress)
  const [error, setError]     = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await client.get('/self-efficacy/', { params: { lang } })
        if (cancelled) return
        setData(res.data)
        setAnswers(res.data.answers || {})
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.status === 403
            ? t('aiCompetency.teachersOnly')
            : t('aiCompetency.loadError'))
        }
      }
    })()
    return () => { cancelled = true }
  }, [t, lang])

  const total = data?.total ?? 24
  const answeredCount = Object.keys(answers).length
  const allAnswered = total > 0 && answeredCount >= total

  const setAnswer = (qid, value) =>
    setAnswers(prev => ({ ...prev, [String(qid)]: value }))

  const persist = async (finish) => {
    setSaving(true)
    setError('')
    try {
      const res = await client.post('/self-efficacy/', { answers }, { params: { lang } })
      setData(res.data)
      setAnswers(res.data.answers || {})
      // Fully finished (first completion or a finished retake) → show results.
      if (res.data.completed && !res.data.retaking) {
        setEditing(false)
        updateUser({
          profile: {
            ...user.profile,
            competency_score: BAND_TO_SCORE[res.data.overall_band] ?? user.profile?.competency_score,
          },
        })
      } else if (!finish) {
        navigate('/profile')
      }
    } catch {
      setError(t('aiCompetency.saveError'))
    } finally {
      setSaving(false)
    }
  }

  // Start a fresh attempt — only reachable while an admin has opened the retake.
  // The completed results stay intact server-side until the retake is finished.
  const retake = async () => {
    setSaving(true)
    setError('')
    try {
      const res = await client.post('/self-efficacy/retake/', null, { params: { lang } })
      setData(res.data)
      setAnswers(res.data.answers || {})
      setEditing(true)
    } catch {
      setError(t('aiCompetency.saveError'))
    } finally {
      setSaving(false)
    }
  }

  if (error && !data) {
    return (
      <div className="aic-page">
        <p className="aic-error">{error}</p>
      </div>
    )
  }
  if (!data) return <div className="aic-page"><p className="aic-loading">{t('common.loading')}</p></div>

  const bandLabel = (band) => band ? t(`aiCompetency.bands.${band}`) : '—'

  // ── Results view (shown once completed unless actively retaking) ──────────
  if (data.completed && !editing) {
    return (
      <div className="aic-page">
        <div className="aic-header">
          <h1 className="aic-title">{t('aiCompetency.resultsTitle')}</h1>
          <p className="aic-subtitle">{t('aiCompetency.resultsSubtitle')}</p>
        </div>

        {data.overall_band && (
          <div className={`aic-overall aic-band--${data.overall_band}`}>
            <span className="aic-overall-label">{t('aiCompetency.overall')}</span>
            <span className="aic-overall-band">{bandLabel(data.overall_band)}</span>
            <span className="aic-overall-avg">{data.overall_average?.toFixed(2)}</span>
          </div>
        )}

        <div className="aic-results">
          {data.dimensions.map(dim => (
            <div key={dim.slug} className="aic-result-row">
              <div className="aic-result-head">
                <span className="aic-result-name">{dim.name}</span>
                <span className={`aic-badge aic-band--${dim.band}`}>{bandLabel(dim.band)}</span>
              </div>
              <div className="aic-bar-track">
                <div
                  className={`aic-bar-fill aic-band--${dim.band}`}
                  style={{ width: `${((dim.average ?? 0) / 5) * 100}%` }}
                />
              </div>
              <span className="aic-result-avg">{dim.average?.toFixed(2) ?? '—'} / 5</span>
            </div>
          ))}
        </div>

        <div className="aic-footer">
          {/* A retake already in progress resumes its draft; otherwise a new
              retake can only be started while an admin has opened the window. */}
          {data.retaking ? (
            <button className="aic-btn aic-btn--ghost" onClick={() => setEditing(true)} disabled={saving}>
              {t('aiCompetency.resume')}
            </button>
          ) : data.can_retake && (
            <button className="aic-btn aic-btn--ghost" onClick={retake} disabled={saving}>
              {saving ? t('aiCompetency.saving') : t('aiCompetency.retake')}
            </button>
          )}
          <button className="aic-btn aic-btn--primary" onClick={() => navigate('/profile')}>
            {t('aiCompetency.backToProfile')}
          </button>
        </div>
      </div>
    )
  }

  // ── Questionnaire view ───────────────────────────────────────────────────
  return (
    <div className="aic-page">
      <div className="aic-header">
        <h1 className="aic-title">{t('aiCompetency.title')}</h1>
        <p className="aic-subtitle">{t('aiCompetency.subtitle')}</p>
        <div className="aic-progress">
          <div className="aic-progress-track">
            <div className="aic-progress-fill" style={{ width: `${(answeredCount / total) * 100}%` }} />
          </div>
          <span className="aic-progress-label">
            {t('aiCompetency.answeredOf', { answered: answeredCount, total })}
          </span>
        </div>
      </div>

      {data.dimensions.map(dim => (
        <section key={dim.slug} className="aic-dimension">
          <h2 className="aic-dimension-name">{dim.name}</h2>
          {dim.questions.map(q => (
            <div key={q.id} className="aic-question">
              <p className="aic-question-text">{q.text}</p>
              <div className="aic-likert" role="radiogroup" aria-label={q.text}>
                {LIKERT.map((value, i) => {
                  const selected = answers[String(q.id)] === value
                  return (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      className={`aic-likert-opt${selected ? ' aic-likert-opt--on' : ''}`}
                      onClick={() => setAnswer(q.id, value)}
                    >
                      <span className="aic-likert-dot" />
                      <span className="aic-likert-label">{t(`aiCompetency.likert.${LIKERT_KEYS[i]}`)}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </section>
      ))}

      {error && <p className="aic-error">{error}</p>}

      <div className="aic-footer">
        <button className="aic-btn aic-btn--ghost" onClick={() => navigate('/')} disabled={saving}>
          {t('aiCompetency.skipForNow')}
        </button>
        <div className="aic-footer-right">
          <button className="aic-btn aic-btn--ghost" onClick={() => persist(false)} disabled={saving || answeredCount === 0}>
            {t('aiCompetency.saveAndExit')}
          </button>
          <button className="aic-btn aic-btn--primary" onClick={() => persist(true)} disabled={saving || !allAnswered}>
            {saving ? t('aiCompetency.saving') : <><Check size={16} /> {t('aiCompetency.finish')}</>}
          </button>
        </div>
      </div>
    </div>
  )
}
