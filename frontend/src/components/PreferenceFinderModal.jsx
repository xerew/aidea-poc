import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { X, Sparkles } from 'lucide-react'
import { Trans, useTranslation } from 'react-i18next'
import client from '../api/client'
import './PreferenceFinderModal.css'

PreferenceFinderModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onComplete: PropTypes.func.isRequired,
}

export default function PreferenceFinderModal({ open, onClose, onComplete }) {
  const { t } = useTranslation()
  const STYLE_LABELS = {
    video: t('profile.finder.styles.video'),
    text: t('profile.finder.styles.text'),
    visual: t('profile.finder.styles.visual'),
    interactive: t('profile.finder.styles.interactive'),
  }
  const [questions, setQuestions] = useState(null)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState({})   // { [questionId]: optionId }
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setQuestions(null)
    setStep(0)
    setAnswers({})
    setResult(null)
    setError('')
    client.get('/preference-quiz/')
      .then(res => setQuestions(res.data))
      .catch(() => setError(t('profile.finder.loadFailed')))
  }, [open, t])

  if (!open) return null

  const current = questions?.[step]
  const isLast = questions && step === questions.length - 1
  const chosen = current ? answers[current.id] : undefined

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        answers: Object.entries(answers).map(([questionId, optionId]) => ({
          question_id: Number(questionId), option_id: optionId,
        })),
      }
      const res = await client.post('/preference-quiz/', payload)
      setResult(res.data)
      onComplete(res.data.learning_style)
    } catch {
      setError(t('profile.finder.saveFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  const resultStyleLabel = result ? (STYLE_LABELS[result.learning_style] ?? result.label) : ''

  return (
    <div className="pf-overlay" onClick={onClose}>
      <div className="pf-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="pf-close" aria-label={t('profile.finder.close')} onClick={onClose}><X size={18} /></button>

        {error && <p className="pf-error">{error}</p>}

        {!error && !questions && <p className="pf-loading">{t('profile.finder.loading')}</p>}

        {!error && questions && questions.length === 0 && (
          <p className="pf-loading">{t('profile.finder.noQuestions')}</p>
        )}

        {!error && questions && questions.length > 0 && !result && current && (
          <>
            <div className="pf-head">
              <Sparkles size={18} className="pf-head-icon" />
              <h2>{t('profile.finder.title')}</h2>
            </div>
            <div className="pf-progress">
              <div className="pf-progress-fill" style={{ width: `${((step + 1) / questions.length) * 100}%` }} />
            </div>
            <p className="pf-counter">
              {t('profile.finder.questionCounter', { current: step + 1, total: questions.length })}
            </p>
            <p className="pf-question">{current.text}</p>
            <div className="pf-options">
              {current.options.map(opt => (
                <button
                  type="button"
                  key={opt.id}
                  className={`pf-option ${chosen === opt.id ? 'pf-option--selected' : ''}`}
                  onClick={() => setAnswers(prev => ({ ...prev, [current.id]: opt.id }))}
                >
                  {opt.text}
                </button>
              ))}
            </div>
            <div className="pf-nav">
              {step > 0 && (
                <button type="button" className="pf-btn pf-btn--ghost" onClick={() => setStep(s => s - 1)}>{t('common.back')}</button>
              )}
              {!isLast && (
                <button type="button" className="pf-btn" disabled={chosen === undefined} onClick={() => setStep(s => s + 1)}>
                  {t('common.next')}
                </button>
              )}
              {isLast && (
                <button type="button" className="pf-btn" disabled={chosen === undefined || submitting} onClick={handleSubmit}>
                  {submitting ? t('profile.finder.working') : t('profile.finder.seeResult')}
                </button>
              )}
            </div>
          </>
        )}

        {result && (
          <div className="pf-result">
            <Sparkles size={28} className="pf-result-icon" />
            <h2>
              <Trans
                i18nKey="profile.finder.resultTitle"
                values={{ style: resultStyleLabel }}
                components={{ styleSpan: <span className="pf-result-style" /> }}
              />
            </h2>
            <p className="pf-result-sub">
              {t('profile.finder.resultSub', { style: resultStyleLabel.toLowerCase() })}
            </p>
            <button type="button" className="pf-btn" onClick={onClose}>{t('profile.finder.done')}</button>
          </div>
        )}
      </div>
    </div>
  )
}
