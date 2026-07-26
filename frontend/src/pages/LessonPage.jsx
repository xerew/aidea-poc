import { useEffect, useState, useCallback, useRef } from 'react'
import PropTypes from 'prop-types'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, CheckCircle2, Circle,
  Video, FileText, HelpCircle, Image, FileIcon, ClipboardList,
  Paperclip, Link2, X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import HtmlContent from '../components/lesson/HtmlContent'
import MediaItem from '../components/lesson/MediaItem'
import './LessonPage.css'

// ─── Lesson-type icons ───────────────────────────────────────────────────────

const TYPE_ICONS = {
  video:      Video,
  text:       FileText,
  quiz:       HelpCircle,
  image:      Image,
  pdf:        FileIcon,
  assignment: ClipboardList,
}

function typeMetaFor(t, type) {
  const key = TYPE_ICONS[type] ? type : 'text'
  return { label: t(`lesson.type.${key}`), Icon: TYPE_ICONS[key] }
}

TypeIcon.propTypes = { type: PropTypes.string.isRequired, size: PropTypes.number }

function TypeIcon({ type, size = 16 }) {
  const Icon = TYPE_ICONS[type] ?? TYPE_ICONS.text
  return <Icon size={size} />
}

// ─── Lesson content components ───────────────────────────────────────────────

const lessonShape = PropTypes.shape({
  id:           PropTypes.number,
  title:        PropTypes.string,
  content:      PropTypes.string,
  media_items:  PropTypes.array,
  quiz_data:    PropTypes.array,
  lesson_type:  PropTypes.string,
  is_completed: PropTypes.bool,
  quiz_review:  PropTypes.shape({
    selected: PropTypes.array,
    results:  PropTypes.array,
  }),
  assignment_submission: PropTypes.object,
})

ContentLesson.propTypes = { lesson: lessonShape.isRequired }
function ContentLesson({ lesson }) {
  const { t } = useTranslation()
  const blocks = lesson.media_items ?? []
  // Back-compat: a legacy media lesson may still hold a single URL in content.
  const legacy = !blocks.length && ['video', 'pdf', 'image'].includes(lesson.lesson_type) && lesson.content
    ? [{ type: lesson.lesson_type, url: lesson.content, caption: '' }]
    : []
  const allBlocks = blocks.length ? blocks : legacy
  const bodyHtml = lesson.lesson_type === 'text' ? lesson.content : ''

  if (!bodyHtml && !allBlocks.length) {
    return <div className="lp-content-card"><p className="lp-empty">{t('lesson.noContent')}</p></div>
  }
  return (
    <div className="lp-content-card">
      {bodyHtml && (
        <div className="lp-text-body">
          <HtmlContent content={bodyHtml} className="lp-text-content" />
        </div>
      )}
      {allBlocks.map((block, i) => (block.type === 'text'
        ? <div key={i} className="lp-text-body"><HtmlContent content={block.html} className="lp-text-content" /></div>
        : <MediaItem key={i} item={block} />
      ))}
    </div>
  )
}

AssignmentLesson.propTypes = {
  lesson: lessonShape.isRequired,
  courseId: PropTypes.string.isRequired,
  onSubmissionChange: PropTypes.func.isRequired,
}
const ATTACHMENT_ICONS = { image: Image, file: FileIcon, video: Video }

function AssignmentLesson({ lesson, courseId, onSubmissionChange }) {
  const { t } = useTranslation()
  const submission = lesson.assignment_submission
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
        const { data } = await client.post(
          `/courses/${courseId}/lessons/${lesson.id}/submission-upload/`, form,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        )
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
      const res = await client.post(
        `/courses/${courseId}/lessons/${lesson.id}/submit-assignment/`,
        { text, attachments },
      )
      onSubmissionChange(res.data)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('lesson.assignment.submitFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="lp-content-card">
      <div className="lp-assignment-body">
        <h3 className="lp-assignment-heading">{t('lesson.assignment.instructions')}</h3>
        <p className="lp-text-content">{lesson.content || t('lesson.assignment.noInstructions')}</p>

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

        {/* Attachments */}
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
    </div>
  )
}

QuizLesson.propTypes = {
  lesson:     lessonShape.isRequired,
  onComplete: PropTypes.func.isRequired,
  courseId:   PropTypes.string.isRequired,
}
function QuizLesson({ lesson, onComplete, courseId }) {
  const { t } = useTranslation()
  const questions = lesson.quiz_data ?? []
  const review = lesson.quiz_review
  const isReview = Boolean(lesson.is_completed && review?.selected?.length)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})     // { [qIdx]: selectedOption }
  const [feedback, setFeedback] = useState({})   // { [qIdx]: {correct, correct_index} }

  if (questions.length === 0) {
    return <div className="lp-content-card"><p className="lp-empty">{t('lesson.quiz.noQuestions')}</p></div>
  }

  const q = questions[currentIdx]
  const isLastQuestion = currentIdx === questions.length - 1
  const answered = isReview || answers[currentIdx] !== undefined

  const handleSelect = async (optionIdx) => {
    if (answered) return
    setAnswers(prev => ({ ...prev, [currentIdx]: optionIdx }))
    try {
      const res = await client.post(
        `/courses/${courseId}/lessons/${lesson.id}/quiz-check/`,
        { question_index: currentIdx, selected: optionIdx },
      )
      setFeedback(prev => ({ ...prev, [currentIdx]: res.data }))
    } catch { /* leave selected highlight only */ }

    if (isLastQuestion) {
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
    <div className="lp-content-card lp-quiz-card">
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

LessonContent.propTypes = {
  lesson:             lessonShape.isRequired,
  onComplete:         PropTypes.func.isRequired,
  onSubmissionChange: PropTypes.func,
  courseId:           PropTypes.string,
}
function LessonContent({ lesson, onComplete, onSubmissionChange, courseId }) {
  switch (lesson.lesson_type) {
    case 'assignment': return <AssignmentLesson lesson={lesson} courseId={courseId} onSubmissionChange={onSubmissionChange} />
    case 'quiz':       return <QuizLesson key={lesson.id} lesson={lesson} onComplete={onComplete} courseId={courseId} />
    default:           return <ContentLesson lesson={lesson} />
  }
}

// ─── Redirect component (/courses/:id/learn) ─────────────────────────────────

export function LearnRedirect() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return }
    client.get(`/courses/${id}/learn/`)
      .then(res => {
        const lessonId = res.data.first_incomplete_lesson_id
        if (lessonId) {
          navigate(`/courses/${id}/learn/${lessonId}`, { replace: true })
        } else {
          navigate(`/courses/${id}`, { replace: true })
        }
      })
      .catch((err) => setError(
        err.response?.status === 404 ? t('lesson.unavailable') : t('lesson.learnRedirectError'),
      ))
  }, [id, navigate, user, t])

  if (error) return <p className="page-error">{error}</p>
  return <p className="page-loading">{t('common.loading')}</p>
}

// ─── Main LessonPage ──────────────────────────────────────────────────────────

export default function LessonPage() {
  const { t } = useTranslation()
  const { courseId, lessonId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [courseLearn, setCourseLearn] = useState(null)
  const [lesson, setLesson] = useState(null)
  const [note, setNote] = useState('')
  const [completing, setCompleting] = useState(false)
  const [error, setError] = useState('')
  const scrollPctRef = useRef(0)

  // Redirect if not logged in
  useEffect(() => {
    if (!user) navigate('/login', { replace: true })
  }, [user, navigate])

  // Fetch sidebar structure whenever courseId changes
  useEffect(() => {
    client.get(`/courses/${courseId}/learn/`)
      .then(res => setCourseLearn(res.data))
      .catch((err) => setError(
        err.response?.status === 404 ? t('lesson.unavailable') : t('lesson.loadCourseError'),
      ))
  }, [courseId, t])

  // Fetch lesson whenever lessonId changes
  useEffect(() => {
    setLesson(null)
    client.get(`/courses/${courseId}/lessons/${lessonId}/`)
      .then(res => setLesson(res.data))
      .catch(() => setError(t('lesson.loadLessonError')))
  }, [courseId, lessonId, t])

  // Reset note when lesson changes
  useEffect(() => { setNote(''); scrollPctRef.current = 0 }, [lessonId])

  // Track scroll percentage for text lessons
  useEffect(() => {
    if (lesson?.lesson_type !== 'text') return
    const handleScroll = () => {
      const total = document.documentElement.scrollHeight - window.innerHeight
      if (total <= 0) return
      const pct = Math.round((window.scrollY / total) * 100)
      scrollPctRef.current = Math.max(scrollPctRef.current, pct)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lesson?.lesson_type])

  const markComplete = useCallback(async (payload = {}) => {
    if (completing || lesson?.is_completed) return null
    setCompleting(true)
    try {
      const res = await client.post(`/courses/${courseId}/lessons/${lessonId}/complete/`, payload)
      setLesson(prev => ({ ...prev, is_completed: true }))
      setCourseLearn(prev => prev ? {
        ...prev,
        progress_pct: res.data.progress_pct,
        modules: prev.modules.map(mod => ({
          ...mod,
          lessons: mod.lessons.map(lsn =>
            lsn.id === Number(lessonId) ? { ...lsn, is_completed: true } : lsn,
          ),
        })),
      } : prev)
      return res.data.quiz_results ?? null
    } finally {
      setCompleting(false)
    }
  }, [completing, lesson, courseId, lessonId])

  const handleMarkComplete = useCallback(() => {
    const payload = {}
    if (lesson?.lesson_type === 'text') {
      payload.engagement_data = { scroll_pct: scrollPctRef.current }
    }
    markComplete(payload)
  }, [lesson, markComplete])

  const handleSubmissionChange = useCallback((sub) => {
    setLesson(prev => ({ ...prev, assignment_submission: sub }))
  }, [])

  const goTo = (id) => id && navigate(`/courses/${courseId}/learn/${id}`)

  if (error) return <p className="page-error">{error}</p>

  const typeMeta = lesson ? typeMetaFor(t, lesson.lesson_type) : null

  return (
    <div className="lp-page">

      {/* Top bar */}
      <div className="lp-topbar">
        <button className="lp-back" onClick={() => navigate(`/courses/${courseId}`)}>
          <ArrowLeft size={15} /> {t('lesson.backToCourse')}
        </button>
        <span className="lp-course-title">{courseLearn?.title ?? '…'}</span>
        <div />
      </div>

      <div className="lp-body">

        {/* ── Sidebar ── */}
        <aside className="lp-sidebar">
          {courseLearn?.modules.map(mod => (
            <div key={mod.id} className="lp-sidebar-module">
              <p className="lp-sidebar-module-title">
                {t('common.moduleLabel', { order: mod.order, title: mod.title })}
              </p>
              {mod.lessons.map(lsn => (
                <button
                  key={lsn.id}
                  className={`lp-sidebar-lesson ${lsn.id === Number(lessonId) ? 'lp-sidebar-lesson--active' : ''}`}
                  onClick={() => goTo(lsn.id)}
                >
                  <span className="lp-sidebar-type-icon">
                    <TypeIcon type={lsn.lesson_type} size={14} />
                  </span>
                  <span className="lp-sidebar-lesson-info">
                    <span className="lp-sidebar-lesson-title">{lsn.title}</span>
                    {lsn.duration_minutes > 0 && (
                      <span className="lp-sidebar-lesson-dur">{t('common.minutesLabel', { count: lsn.duration_minutes })}</span>
                    )}
                  </span>
                  {lsn.is_completed
                    ? <CheckCircle2 size={18} className="lp-check-done" />
                    : <Circle size={18} className="lp-check-empty" />
                  }
                </button>
              ))}
            </div>
          ))}

          {courseLearn && (
            <div className="lp-sidebar-progress">
              <div className="lp-sidebar-progress-row">
                <span>{t('common.progress')}</span>
                <span>{courseLearn.progress_pct}%</span>
              </div>
              <div className="lp-sidebar-progress-bar">
                <div
                  className="lp-sidebar-progress-fill"
                  style={{ width: `${courseLearn.progress_pct}%` }}
                />
              </div>
            </div>
          )}
        </aside>

        {/* ── Main ── */}
        <main className="lp-main">
          {!lesson ? (
            <p className="page-loading">{t('lesson.loadingLesson')}</p>
          ) : (
            <>
              {/* Lesson header */}
              <div className="lp-lesson-header">
                <span className="lp-type-tag">
                  <TypeIcon type={lesson.lesson_type} size={14} />
                  {typeMeta.label}
                </span>
                <h1 className="lp-lesson-title">{lesson.title}</h1>
                {lesson.description && (
                  <p className="lp-lesson-desc">{lesson.description}</p>
                )}
              </div>

              {/* Lesson content */}
              <LessonContent lesson={lesson} onComplete={markComplete} onSubmissionChange={handleSubmissionChange} courseId={courseId} />

              {/* Navigation */}
              <div className="lp-nav">
                <button
                  className="lp-nav-btn"
                  disabled={!lesson.prev_lesson_id}
                  onClick={() => goTo(lesson.prev_lesson_id)}
                >
                  &#8249; {t('common.previous')}
                </button>

                {/* Hide Mark Complete for quizzes and assignments — they complete via their own flows */}
                {lesson.lesson_type !== 'quiz' && lesson.lesson_type !== 'assignment' && (
                  <button
                    className={`lp-complete-btn ${lesson.is_completed ? 'lp-complete-btn--done' : ''}`}
                    onClick={handleMarkComplete}
                    disabled={completing || lesson.is_completed}
                  >
                    {lesson.is_completed ? t('common.completedCheck') : completing ? t('common.saving') : t('lesson.markComplete')}
                  </button>
                )}
                {lesson.lesson_type === 'quiz' && lesson.is_completed && (
                  <span className="lp-complete-btn lp-complete-btn--done">{t('common.completedCheck')}</span>
                )}
                {lesson.lesson_type === 'assignment' && lesson.is_completed && (
                  <span className="lp-complete-btn lp-complete-btn--done">{t('common.completedCheck')}</span>
                )}
                {lesson.lesson_type === 'assignment' && !lesson.is_completed
                  && lesson.assignment_submission?.status === 'pending' && (
                  <span className="lp-complete-btn lp-complete-btn--disabled">{t('lesson.pendingReview')}</span>
                )}

                <button
                  className="lp-nav-btn lp-nav-btn--primary"
                  disabled={!lesson.next_lesson_id}
                  onClick={() => goTo(lesson.next_lesson_id)}
                >
                  {t('common.next')} &#8250;
                </button>
              </div>

              {/* Notes */}
              <div className="lp-notes">
                <h3 className="lp-notes-title">{t('lesson.yourNotesTitle')}</h3>
                <textarea
                  className="lp-notes-input"
                  placeholder={t('lesson.notesPlaceholder')}
                  value={note}
                  onChange={e => setNote(e.target.value)}
                />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
