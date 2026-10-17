import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ClipboardCheck, ChevronDown, ChevronUp, Image, FileIcon, Video, Sparkles, RotateCcw } from 'lucide-react'

const ATTACHMENT_ICONS = { image: Image, file: FileIcon, video: Video }
import PropTypes from 'prop-types'
import client from '../api/client'
import AIReviewBox from '../components/reviews/AIReviewBox'
import { disagrees } from '../components/reviews/aiReview'
import './ReviewsPage.css'

const FILTERS = ['', 'ai_approve', 'ai_unsure', 'flagged', 'auto_approved']
const REASONS = ['missed_evidence', 'too_strict', 'too_lenient', 'misread_image', 'other']

SubmissionRow.propTypes = {
  sub: PropTypes.object.isRequired,
  onDone: PropTypes.func.isRequired,
}

function SubmissionRow({ sub, onDone }) {
  const { t } = useTranslation()
  const [openRow, setOpenRow] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [usedAI, setUsedAI] = useState(false)
  const [pendingAction, setPendingAction] = useState('')   // waiting for the "why disagree" answer
  const [reason, setReason] = useState('')
  const [example, setExample] = useState(null)              // {verdict, reason} while the form is open
  const [exampleMsg, setExampleMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const ai = sub.ai_review
  const autoApproved = sub.status === 'approved'

  const send = async (action, why) => {
    setBusy(true)
    setError('')
    try {
      await client.post(`/reviews/${sub.id}/`, {
        action, feedback, used_ai_feedback: usedAI, disagreement_reason: why,
      })
      onDone(sub.id)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('reviews.actionFailed'))
      setBusy(false)
    }
  }

  const act = (action) => {
    if (action === 'request_changes' && !feedback.trim()) {
      setError(t('reviews.feedbackRequired'))
      return
    }
    if (ai?.status === 'done' && disagrees(ai.verdict, action)) {
      setPendingAction(action)
      return
    }
    send(action, '')
  }

  const addExample = async () => {
    setExampleMsg('')
    try {
      await client.post(`/reviews/${sub.id}/example/`, example)
      setExample(null)
      setExampleMsg(t('reviews.ai.exampleAdded'))
    } catch (err) {
      setExampleMsg(err.response?.data?.detail ?? t('reviews.actionFailed'))
    }
  }

  const reopen = async () => {
    setBusy(true)
    setError('')
    try {
      await client.post(`/reviews/${sub.id}/reopen/`)
      onDone(sub.id)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('reviews.actionFailed'))
      setBusy(false)
    }
  }

  return (
    <div className="rv-row">
      <div className="rv-row-head">
        <div className="rv-row-title">
          <Link className="rv-learner" to={`/users/${sub.learner_id}`}>{sub.learner_name}</Link>
          <span className="rv-meta">{sub.course_title} · {sub.module_title} · {sub.lesson_title}</span>
        </div>
        <button type="button" className="rv-row-toggle" onClick={() => setOpenRow(o => !o)}>
          {ai?.status === 'done' && !autoApproved && (
            <span className={`rv-ai-chip rv-ai-chip--${ai.verdict}`}><Sparkles size={12} /> {t(`reviews.ai.verdict.${ai.verdict}`)}</span>
          )}
          {autoApproved && <span className="rv-ai-chip rv-ai-chip--approve">{t('reviews.ai.approvedByAI')}</span>}
          <span className="rv-date">{new Date(sub.submitted_at).toLocaleDateString()}</span>
          {openRow ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {openRow && (
        <div className="rv-row-body">
          {sub.text && <p className="rv-text">{sub.text}</p>}
          {sub.attachments?.length > 0 && (
            <div className="rv-attachments">
              {sub.attachments.map((att, idx) => {
                const Icon = ATTACHMENT_ICONS[att.type] ?? FileIcon
                if (att.type === 'image') {
                  return (
                    <a key={idx} href={att.url} target="_blank" rel="noreferrer" className="rv-attach-thumb">
                      <img src={att.url} alt={att.name || ''} />
                    </a>
                  )
                }
                return (
                  <a key={idx} href={att.url} target="_blank" rel="noreferrer" className="rv-attach-chip">
                    <Icon size={15} />
                    <span>{att.name || att.url}</span>
                  </a>
                )
              })}
            </div>
          )}
          {ai && (
            <AIReviewBox
              review={ai}
              onUseFeedback={autoApproved ? undefined : (text) => { setFeedback(text); setUsedAI(true) }}
            />
          )}
          {sub.feedback && (
            <p className="rv-prev-feedback"><strong>{t('reviews.previousFeedback')}</strong> {sub.feedback}</p>
          )}

          {autoApproved ? (
            <div className="rv-actions">
              <button type="button" className="rv-btn rv-btn--changes" disabled={busy} onClick={reopen}>
                <RotateCcw size={14} /> {t('reviews.ai.reopen')}
              </button>
            </div>
          ) : (
            <>
              <textarea
                className="rv-feedback-input"
                placeholder={t('reviews.feedbackPlaceholder')}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              />
              {error && <p className="rv-error">{error}</p>}
              {pendingAction ? (
                <div className="rv-disagree">
                  <label className="rv-disagree-label">
                    {t('reviews.ai.whyDisagree')}
                    <select value={reason} onChange={(e) => setReason(e.target.value)}>
                      <option value="">—</option>
                      {REASONS.map(r => <option key={r} value={r}>{t(`reviews.ai.reason.${r}`)}</option>)}
                    </select>
                  </label>
                  <button type="button" className="rv-btn" disabled={busy} onClick={() => send(pendingAction, '')}>
                    {t('reviews.ai.skip')}
                  </button>
                  <button type="button" className="rv-btn rv-btn--approve" disabled={busy || !reason}
                    onClick={() => send(pendingAction, reason)}>
                    {busy ? t('reviews.working') : t('reviews.ai.send')}
                  </button>
                </div>
              ) : (
                <div className="rv-actions">
                  <button type="button" className="rv-btn rv-btn--changes" disabled={busy} onClick={() => act('request_changes')}>
                    {t('reviews.requestChanges')}
                  </button>
                  <button type="button" className="rv-btn rv-btn--approve" disabled={busy} onClick={() => act('approve')}>
                    {busy ? t('reviews.working') : t('reviews.approve')}
                  </button>
                </div>
              )}
            </>
          )}
          {autoApproved && error && <p className="rv-error">{error}</p>}

          {ai?.example_allowed && (
            <div className="rv-example">
              {example ? (
                <div className="rv-example-form">
                  <select value={example.verdict} onChange={(e) => setExample({ ...example, verdict: e.target.value })}>
                    <option value="approve">{t('authoring.aiReview.verdictApprove')}</option>
                    <option value="changes_requested">{t('authoring.aiReview.verdictChanges')}</option>
                  </select>
                  <input type="text" placeholder={t('authoring.aiReview.reason')} value={example.reason}
                    onChange={(e) => setExample({ ...example, reason: e.target.value })} />
                  <button type="button" className="rv-btn" onClick={addExample}>{t('authoring.aiReview.addExample')}</button>
                  <button type="button" className="rv-btn" onClick={() => setExample(null)}>{t('reviews.ai.cancel')}</button>
                </div>
              ) : (
                <button type="button" className="rv-link-btn"
                  onClick={() => { setExample({ verdict: 'approve', reason: '' }); setExampleMsg('') }}>
                  {t('reviews.ai.useAsExample')}
                </button>
              )}
              {exampleMsg && <span className="rv-example-msg">{exampleMsg}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ReviewsPage() {
  const { t } = useTranslation()
  const [filter, setFilter] = useState('')
  const [subs, setSubs] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/reviews/', { params: filter ? { filter } : {} })
      .then(res => setSubs(res.data))
      .catch(() => setError(t('reviews.loadError')))
  }, [filter, t])

  if (error) return <p className="page-error">{error}</p>

  return (
    <div className="reviews-page">
      <div className="rv-header">
        <ClipboardCheck size={22} className="rv-header-icon" />
        <div>
          <h1>{t('reviews.title')}</h1>
          <p className="rv-sub">{t('reviews.subtitle')}</p>
        </div>
      </div>

      <div className="rv-filter">
        <select value={filter} aria-label={t('reviews.ai.filterLabel')}
          onChange={(e) => { setFilter(e.target.value); setSubs(null) }}>
          {FILTERS.map(f => <option key={f} value={f}>{t(`reviews.ai.filter.${f || 'all'}`)}</option>)}
        </select>
      </div>

      {!subs
        ? <p className="page-loading">{t('common.loading')}</p>
        : subs.length === 0
          ? <p className="rv-empty">{t('reviews.empty')}</p>
          : subs.map(sub => (
              <SubmissionRow key={sub.id} sub={sub} onDone={(id) => setSubs(prev => prev.filter(s => s.id !== id))} />
            ))}
    </div>
  )
}
