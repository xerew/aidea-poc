import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { X, Sparkles } from 'lucide-react'
import client from '../api/client'
import './PreferenceFinderModal.css'

const STYLE_LABELS = { video: 'Video', text: 'Text', visual: 'Visual', interactive: 'Interactive' }

PreferenceFinderModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onComplete: PropTypes.func.isRequired,
}

export default function PreferenceFinderModal({ open, onClose, onComplete }) {
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
      .catch(() => setError('Could not load the questions. Please try again later.'))
  }, [open])

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
      setError('Something went wrong saving your result. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="pf-overlay" onClick={onClose}>
      <div className="pf-modal" onClick={(e) => e.stopPropagation()}>
        <button className="pf-close" aria-label="Close" onClick={onClose}><X size={18} /></button>

        {error && <p className="pf-error">{error}</p>}

        {!error && !questions && <p className="pf-loading">Loading questions…</p>}

        {!error && questions && questions.length === 0 && (
          <p className="pf-loading">No questions are configured yet. Check back soon!</p>
        )}

        {!error && questions && questions.length > 0 && !result && current && (
          <>
            <div className="pf-head">
              <Sparkles size={18} className="pf-head-icon" />
              <h2>Find your learning preference</h2>
            </div>
            <div className="pf-progress">
              <div className="pf-progress-fill" style={{ width: `${((step + 1) / questions.length) * 100}%` }} />
            </div>
            <p className="pf-counter">Question {step + 1} of {questions.length}</p>
            <p className="pf-question">{current.text}</p>
            <div className="pf-options">
              {current.options.map(opt => (
                <button
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
                <button className="pf-btn pf-btn--ghost" onClick={() => setStep(s => s - 1)}>Back</button>
              )}
              {!isLast && (
                <button className="pf-btn" disabled={chosen === undefined} onClick={() => setStep(s => s + 1)}>
                  Next
                </button>
              )}
              {isLast && (
                <button className="pf-btn" disabled={chosen === undefined || submitting} onClick={handleSubmit}>
                  {submitting ? 'Working…' : 'See my result'}
                </button>
              )}
            </div>
          </>
        )}

        {result && (
          <div className="pf-result">
            <Sparkles size={28} className="pf-result-icon" />
            <h2>You learn best with <span className="pf-result-style">{STYLE_LABELS[result.learning_style] ?? result.label}</span> content</h2>
            <p className="pf-result-sub">
              We saved this as your preferred learning format — recommendations will favour
              {' '}{(STYLE_LABELS[result.learning_style] ?? result.label).toLowerCase()} courses.
              You can change it anytime in Learning Preferences.
            </p>
            <button className="pf-btn" onClick={onClose}>Done</button>
          </div>
        )}
      </div>
    </div>
  )
}
