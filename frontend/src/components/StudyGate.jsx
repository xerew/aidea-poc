import PropTypes from 'prop-types'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FlaskConical, X } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './StudyGate.css'

function ConsentModal({ onDone }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)

  const respond = async (consent) => {
    setBusy(true)
    try {
      await client.post('/study/consent/', { consent })
      onDone()
    } catch { setBusy(false) }
  }

  return (
    <div className="study-overlay">
      <div className="study-modal">
        <div className="study-modal-head">
          <FlaskConical size={20} />
          <h2>{t('study.consent.title')}</h2>
          <button className="study-close" onClick={onDone} aria-label={t('common.dismiss')}><X size={18} /></button>
        </div>
        <p className="study-body">{t('study.consent.body')}</p>
        <p className="study-note">{t('study.consent.voluntary')}</p>
        <div className="study-actions">
          <button className="study-btn-secondary" disabled={busy} onClick={() => respond(false)}>
            {t('study.consent.decline')}
          </button>
          <button className="study-btn-primary" disabled={busy} onClick={() => respond(true)}>
            {t('study.consent.join')}
          </button>
        </div>
      </div>
    </div>
  )
}
ConsentModal.propTypes = { onDone: PropTypes.func.isRequired }

function AssessmentModal({ phase, onDone, onClose }) {
  const { t } = useTranslation()
  const [questions, setQuestions] = useState(null)
  const [answers, setAnswers] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/study/assessment/')
      .then(res => setQuestions(res.data.questions))
      .catch(() => setError(t('study.assessment.loadError')))
  }, [t])

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      await client.post('/study/assessment/', { phase, answers })
      onDone()
    } catch (err) {
      setError(err?.response?.data?.detail || t('study.assessment.submitError'))
      setSubmitting(false)
    }
  }

  const allAnswered = questions && questions.every(q => answers[q.id] != null)

  return (
    <div className="study-overlay">
      <div className="study-modal study-modal--wide">
        <div className="study-modal-head">
          <FlaskConical size={20} />
          <h2>{phase === 'pre' ? t('study.assessment.preTitle') : t('study.assessment.postTitle')}</h2>
          {onClose && <button className="study-close" onClick={onClose} aria-label={t('common.dismiss')}><X size={18} /></button>}
        </div>
        <p className="study-body">{t('study.assessment.intro')}</p>

        {!questions ? (
          <p className="study-note">{t('common.loading')}</p>
        ) : (
          <div className="study-questions">
            {questions.map((q, i) => (
              <div key={q.id} className="study-question">
                <p className="study-q-text">{i + 1}. {q.text}</p>
                {q.options.map(o => (
                  <label key={o.id} className="study-option">
                    <input
                      type="radio"
                      name={`q${q.id}`}
                      checked={answers[q.id] === o.id}
                      onChange={() => setAnswers(prev => ({ ...prev, [q.id]: o.id }))}
                    />
                    <span>{o.text}</span>
                  </label>
                ))}
              </div>
            ))}
          </div>
        )}

        {error && <p className="study-error">{error}</p>}
        <div className="study-actions">
          <button className="study-btn-primary" disabled={submitting || !allAnswered} onClick={submit}>
            {submitting ? t('study.assessment.submitting') : t('study.assessment.submit')}
          </button>
        </div>
      </div>
    </div>
  )
}
AssessmentModal.propTypes = {
  phase: PropTypes.oneOf(['pre', 'post']).isRequired,
  onDone: PropTypes.func.isRequired,
  onClose: PropTypes.func,
}

export default function StudyGate() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [status, setStatus] = useState(null)
  const [takingPost, setTakingPost] = useState(false)

  const refetch = useCallback(() => {
    setTakingPost(false)
    client.get('/study/status/').then(res => setStatus(res.data)).catch(() => setStatus(null))
  }, [])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    client.get('/study/status/')
      .then(res => { if (active) setStatus(res.data) })
      .catch(() => { if (active) setStatus(null) })
    return () => { active = false }
  }, [user])

  if (!status?.enabled || !status.is_teacher) return null

  if (status.needs_consent) return <ConsentModal onDone={refetch} />

  if (status.in_study && status.pending_phase === 'pre' && status.has_assessment) {
    return <AssessmentModal phase="pre" onDone={refetch} />
  }

  if (status.pending_phase === 'post') {
    return (
      <>
        <div className="study-banner">
          <FlaskConical size={16} />
          <span>{t('study.postPrompt.text')}</span>
          <button className="study-banner-btn" onClick={() => setTakingPost(true)}>
            {t('study.postPrompt.take')}
          </button>
        </div>
        {takingPost && (
          <AssessmentModal phase="post" onDone={refetch} onClose={() => setTakingPost(false)} />
        )}
      </>
    )
  }

  return null
}
