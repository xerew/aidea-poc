import { useState, useRef } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, Circle, Video, Image, FileIcon, Paperclip, Link2, X } from 'lucide-react'
import client from '../../api/client'
import HtmlContent from '../lesson/HtmlContent'
import MediaItem from '../lesson/MediaItem'
import TypeIcon from './TypeIcon'
import { TYPE_ICONS, resourceShape } from './resourceMeta'

const base = (courseId, activityId, resourceId) =>
  `/courses/${courseId}/lessons/${activityId}/resources/${resourceId}`

// ─── Text / media ────────────────────────────────────────────────────────────

TextBody.propTypes = { resource: resourceShape.isRequired }
function TextBody({ resource }) {
  const { t } = useTranslation()
  if (!resource.content) return <p className="lp-empty">{t('lesson.noContent')}</p>
  return (
    <div className="lp-text-body">
      <HtmlContent content={resource.content} className="lp-text-content" />
    </div>
  )
}

MediaBody.propTypes = { resource: resourceShape.isRequired }
function MediaBody({ resource }) {
  const { t } = useTranslation()
  if (!resource.url) return <p className="lp-empty">{t('lesson.noContent')}</p>
  return <MediaItem item={{ type: resource.type, url: resource.url, caption: resource.caption }} />
}

// ─── Quiz ────────────────────────────────────────────────────────────────────

QuizBody.propTypes = {
  resource:   resourceShape.isRequired,
  endpoint:   PropTypes.string.isRequired,
  onComplete: PropTypes.func.isRequired,
}
function QuizBody({ resource, endpoint, onComplete }) {
  const { t } = useTranslation()
  const questions = resource.quiz_data ?? []
  const review = resource.quiz_review
  const isReview = Boolean(resource.is_completed && review?.selected?.length)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})     // { [qIdx]: selectedOption }
  const [feedback, setFeedback] = useState({})   // { [qIdx]: {correct, correct_index} }

  if (questions.length === 0) {
    return <p className="lp-empty">{t('lesson.quiz.noQuestions')}</p>
  }

  const q = questions[currentIdx]
  const isLastQuestion = currentIdx === questions.length - 1
  const answered = isReview || answers[currentIdx] !== undefined

  const handleSelect = async (optionIdx) => {
    if (answered) return
    setAnswers(prev => ({ ...prev, [currentIdx]: optionIdx }))
    try {
      const res = await client.post(`${endpoint}/quiz-check/`, {
        question_index: currentIdx, selected: optionIdx,
      })
      setFeedback(prev => ({ ...prev, [currentIdx]: res.data }))
    } catch { /* leave selected highlight only */ }

    if (isLastQuestion && !resource.is_completed) {
      const finalAnswers = { ...answers, [currentIdx]: optionIdx }
      const answersArray = questions.map((_, i) => finalAnswers[i] ?? -1)
      setTimeout(() => onComplete({ quiz_answers: answersArray }), 1200)
    }
  }

  const selectedOf = (qIdx) => isReview ? review.selected[qIdx] : answers[qIdx]
  const resultOf   = (qIdx) => {
    if (isReview) return { correct: review.results[qIdx], correct_index: null }
    return feedback[qIdx] ?? null
  }

  const getOptionState = (optionIdx) => {
    const selected = selectedOf(currentIdx)
    if (selected === undefined || selected === null) return ''
    const res = resultOf(currentIdx)
    const isSelected = selected === optionIdx
    if (res) {
      if (isSelected) return res.correct ? 'lp-option--correct' : 'lp-option--wrong'
      if (res.correct_index === optionIdx) return 'lp-option--correct'
      return 'lp-option--dimmed'
    }
    return isSelected ? 'lp-option--selected' : 'lp-option--dimmed'
  }

  const badgeFor = (optionIdx) => {
    const selected = selectedOf(currentIdx)
    const res = resultOf(currentIdx)
    if (selected === undefined || selected === null || !res) return null
    if (selected === optionIdx) {
      return res.correct
        ? <span className="lp-option-badge lp-option-badge--correct">{t('lesson.quiz.correct')}</span>
        : <span className="lp-option-badge lp-option-badge--wrong">{t('lesson.quiz.incorrect')}</span>
    }
    if (!res.correct && res.correct_index === optionIdx) {
      return <span className="lp-option-badge lp-option-badge--correct">{t('lesson.quiz.correctAnswer')}</span>
    }
    return null
  }

  return (
    <div className="lp-quiz-card">
      <div className="lp-question-block">
        <p className="lp-question-counter">
          {t('lesson.quiz.questionCounter', { current: currentIdx + 1, total: questions.length })}
          {isReview && t('lesson.quiz.reviewSuffix')}
        </p>
        <p className="lp-question-text">{q.question}</p>
      </div>

      <div className="lp-options">
        {(q.options ?? []).map((opt, i) => (
          <button
            key={i}
            className={`lp-option lp-option--btn ${getOptionState(i)}`}
            onClick={() => handleSelect(i)}
            disabled={answered}
          >
            <span className="lp-option-radio" />
            <span>{opt.text}</span>
            {badgeFor(i)}
          </button>
        ))}
      </div>

      <div className="lp-quiz-nav">
        {currentIdx > 0 && (
          <button className="lp-quiz-arrow" onClick={() => setCurrentIdx(i => i - 1)}>
            {t('lesson.quiz.previousQuestion')}
          </button>
        )}
        {answered && !isLastQuestion && (
          <button
            className="lp-quiz-arrow lp-quiz-arrow--next"
            onClick={() => setCurrentIdx(i => i + 1)}
          >
            {t('lesson.quiz.nextQuestion')}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Assignment ──────────────────────────────────────────────────────────────

const ATTACHMENT_ICONS = { image: Image, file: FileIcon, video: Video }

AssignmentBody.propTypes = {
  resource:           resourceShape.isRequired,
  endpoint:           PropTypes.string.isRequired,
  uploadUrl:          PropTypes.string.isRequired,
  onSubmissionChange: PropTypes.func.isRequired,
}
function AssignmentBody({ resource, endpoint, uploadUrl, onSubmissionChange }) {
  const { t } = useTranslation()
  const submission = resource.submission
  const [text, setText] = useState(submission?.text ?? '')
  const [attachments, setAttachments] = useState(submission?.attachments ?? [])
  const [videoUrl, setVideoUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef(null)

  const status = submission?.status
  const locked = status === 'pending' || status === 'approved'
  const busy = submitting || uploading

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (!files.length) return
    setUploading(true)
    setError('')
    try {
      for (const file of files) {
        const form = new FormData()
        form.append('file', file)
        const { data } = await client.post(uploadUrl, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        setAttachments(prev => [...prev, data])
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? t('lesson.assignment.uploadFailed'))
    } finally {
      setUploading(false)
    }
  }

  const addVideo = () => {
    const url = videoUrl.trim()
    if (!url) return
    setAttachments(prev => [...prev, { type: 'video', url, name: url }])
    setVideoUrl('')
  }

  const removeAttachment = (idx) => setAttachments(prev => prev.filter((_, i) => i !== idx))

  const handleSubmit = async () => {
    if (!text.trim() && attachments.length === 0) {
      setError(t('lesson.assignment.emptySubmission'))
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const res = await client.post(`${endpoint}/submit-assignment/`, { text, attachments })
      onSubmissionChange(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('lesson.assignment.submitFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="lp-assignment-body">
      <h3 className="lp-assignment-heading">{t('lesson.assignment.instructions')}</h3>
      {resource.instructions
        ? <HtmlContent content={resource.instructions} className="lp-text-content" />
        : <p className="lp-text-content">{t('lesson.assignment.noInstructions')}</p>}

      {status === 'pending' && (
        <div className="lp-assignment-banner lp-assignment-banner--pending">
          {t('lesson.assignment.pendingBanner')}
        </div>
      )}
      {status === 'approved' && (
        <div className="lp-assignment-banner lp-assignment-banner--approved">
          {t('lesson.assignment.approved')}{submission.feedback ? ` — ${submission.feedback}` : ''} ✓
        </div>
      )}
      {status === 'changes_requested' && (
        <div className="lp-assignment-banner lp-assignment-banner--changes">
          <strong>{t('lesson.assignment.changesRequested')}</strong> {submission.feedback}
        </div>
      )}

      <h3 className="lp-assignment-heading lp-assignment-heading--response">{t('lesson.assignment.yourResponse')}</h3>
      <textarea
        className="lp-notes-input"
        placeholder={t('lesson.assignment.responsePlaceholder')}
        value={text}
        disabled={locked || submitting}
        onChange={(e) => setText(e.target.value)}
      />

      {attachments.length > 0 && (
        <ul className="lp-attach-list">
          {attachments.map((att, idx) => {
            const Icon = ATTACHMENT_ICONS[att.type] ?? FileIcon
            return (
              <li key={`${att.url}-${idx}`} className="lp-attach-item">
                <Icon size={15} className="lp-attach-icon" />
                <a href={att.url} target="_blank" rel="noreferrer" className="lp-attach-name">
                  {att.name || att.url}
                </a>
                {!locked && (
                  <button
                    type="button"
                    className="lp-attach-remove"
                    onClick={() => removeAttachment(idx)}
                    aria-label={t('lesson.assignment.removeAttachment')}
                  >
                    <X size={14} />
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {!locked && (
        <div className="lp-attach-controls">
          <button
            type="button"
            className="lp-attach-btn"
            onClick={() => fileRef.current?.click()}
            disabled={busy}
          >
            <Paperclip size={15} /> {uploading ? t('lesson.assignment.uploading') : t('lesson.assignment.addFile')}
          </button>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt"
            className="lp-attach-file-input"
            onChange={handleFiles}
          />
          <div className="lp-attach-video">
            <Link2 size={15} className="lp-attach-video-icon" />
            <input
              type="url"
              className="lp-attach-video-input"
              placeholder={t('lesson.assignment.videoLinkPlaceholder')}
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addVideo() } }}
            />
            <button type="button" className="lp-attach-btn" onClick={addVideo} disabled={!videoUrl.trim()}>
              {t('lesson.assignment.addLink')}
            </button>
          </div>
        </div>
      )}

      {error && <p className="lp-assignment-error">{error}</p>}
      {!locked && (
        <button
          type="button"
          className="lp-complete-btn lp-assignment-submit"
          disabled={busy}
          onClick={handleSubmit}
        >
          {submitting
            ? t('lesson.assignment.submitting')
            : status === 'changes_requested' ? t('lesson.assignment.resubmit') : t('lesson.assignment.submit')}
        </button>
      )}
    </div>
  )
}

// ─── One resource: header + body + completion control ───────────────────────

ResourceView.propTypes = {
  resource:           resourceShape.isRequired,
  courseId:           PropTypes.string.isRequired,
  activityId:         PropTypes.string.isRequired,
  onComplete:         PropTypes.func.isRequired,
  onSubmissionChange: PropTypes.func.isRequired,
}
export default function ResourceView({ resource, courseId, activityId, onComplete, onSubmissionChange }) {
  const { t } = useTranslation()
  const [saving, setSaving] = useState(false)
  const endpoint = base(courseId, activityId, resource.id)
  const selfCompletes = !['quiz', 'assignment'].includes(resource.type)

  const complete = async (payload = {}) => {
    if (saving || resource.is_completed) return
    setSaving(true)
    try {
      await onComplete(resource, payload)
    } finally {
      setSaving(false)
    }
  }

  let body
  switch (resource.type) {
    case 'text':
      body = <TextBody resource={resource} />
      break
    case 'quiz':
      body = <QuizBody resource={resource} endpoint={endpoint} onComplete={complete} />
      break
    case 'assignment':
      body = (
        <AssignmentBody
          resource={resource}
          endpoint={endpoint}
          uploadUrl={`/courses/${courseId}/lessons/${activityId}/submission-upload/`}
          onSubmissionChange={(sub) => onSubmissionChange(resource.id, sub)}
        />
      )
      break
    default:
      body = <MediaBody resource={resource} />
  }

  return (
    <section className={`lp-resource ${resource.is_completed ? 'lp-resource--done' : ''}`}>
      <header className="lp-resource-header">
        <span className="lp-resource-type">
          <TypeIcon type={resource.type} size={15} />
          {resource.title || t(`lesson.type.${TYPE_ICONS[resource.type] ? resource.type : 'text'}`)}
        </span>
        {!resource.is_required && (
          <span className="lp-resource-optional">{t('lesson.resource.optional')}</span>
        )}
        {resource.is_completed
          ? <CheckCircle2 size={18} className="lp-check-done" aria-label={t('lesson.resource.done')} />
          : <Circle size={18} className="lp-check-empty" aria-hidden="true" />}
      </header>

      <div className="lp-content-card lp-resource-card">{body}</div>

      {selfCompletes && (
        <div className="lp-resource-footer">
          <button
            type="button"
            className={`lp-complete-btn lp-resource-btn ${resource.is_completed ? 'lp-complete-btn--done' : ''}`}
            onClick={() => complete()}
            disabled={saving || resource.is_completed}
          >
            {resource.is_completed
              ? t('common.completedCheck')
              : saving ? t('common.saving') : t('lesson.resource.markDone')}
          </button>
        </div>
      )}
      {resource.type === 'assignment' && !resource.is_completed
        && resource.submission?.status === 'pending' && (
        <div className="lp-resource-footer">
          <span className="lp-complete-btn lp-complete-btn--disabled">{t('lesson.pendingReview')}</span>
        </div>
      )}
    </section>
  )
}
