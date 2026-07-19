import { useEffect, useState } from 'react'
import { ClipboardCheck, ChevronDown, ChevronUp } from 'lucide-react'
import PropTypes from 'prop-types'
import client from '../api/client'
import './ReviewsPage.css'

SubmissionRow.propTypes = {
  sub: PropTypes.object.isRequired,
  onDone: PropTypes.func.isRequired,
}

function SubmissionRow({ sub, onDone }) {
  const [openRow, setOpenRow] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const act = async (action) => {
    if (action === 'request_changes' && !feedback.trim()) {
      setError('Write feedback before requesting changes.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await client.post(`/reviews/${sub.id}/`, { action, feedback })
      onDone(sub.id)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Action failed. Please try again.')
      setBusy(false)
    }
  }

  return (
    <div className="rv-row">
      <button type="button" className="rv-row-head" onClick={() => setOpenRow(o => !o)}>
        <div className="rv-row-title">
          <span className="rv-learner">{sub.learner_name}</span>
          <span className="rv-meta">{sub.course_title} · {sub.module_title} · {sub.lesson_title}</span>
        </div>
        <span className="rv-date">{new Date(sub.submitted_at).toLocaleDateString()}</span>
        {openRow ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {openRow && (
        <div className="rv-row-body">
          <p className="rv-text">{sub.text}</p>
          {sub.feedback && (
            <p className="rv-prev-feedback"><strong>Previous feedback:</strong> {sub.feedback}</p>
          )}
          <textarea
            className="rv-feedback-input"
            placeholder="Feedback for the learner (required to request changes, optional on approve)…"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          {error && <p className="rv-error">{error}</p>}
          <div className="rv-actions">
            <button type="button" className="rv-btn rv-btn--changes" disabled={busy} onClick={() => act('request_changes')}>
              Request changes
            </button>
            <button type="button" className="rv-btn rv-btn--approve" disabled={busy} onClick={() => act('approve')}>
              {busy ? 'Working…' : 'Approve'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReviewsPage() {
  const [subs, setSubs] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/reviews/')
      .then(res => setSubs(res.data))
      .catch(() => setError('Failed to load the review queue.'))
  }, [])

  if (error) return <p className="page-error">{error}</p>
  if (!subs) return <p className="page-loading">Loading…</p>

  return (
    <div className="reviews-page">
      <div className="rv-header">
        <ClipboardCheck size={22} className="rv-header-icon" />
        <div>
          <h1>Assignment Reviews</h1>
          <p className="rv-sub">Submissions waiting for your review</p>
        </div>
      </div>

      {subs.length === 0
        ? <p className="rv-empty">No submissions waiting for review. 🎉</p>
        : subs.map(sub => (
            <SubmissionRow key={sub.id} sub={sub} onDone={(id) => setSubs(prev => prev.filter(s => s.id !== id))} />
          ))}
    </div>
  )
}
