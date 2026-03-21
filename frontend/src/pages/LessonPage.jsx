import { useEffect, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, Circle,
  Video, FileText, HelpCircle, Image, FileIcon, ClipboardList,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './LessonPage.css'

// ─── Lesson-type icons ───────────────────────────────────────────────────────

const TYPE_META = {
  video:      { label: 'Video',      Icon: Video },
  text:       { label: 'Text',       Icon: FileText },
  quiz:       { label: 'Quiz',       Icon: HelpCircle },
  image:      { label: 'Image',      Icon: Image },
  pdf:        { label: 'PDF',        Icon: FileIcon },
  assignment: { label: 'Assignment', Icon: ClipboardList },
}

TypeIcon.propTypes = { type: PropTypes.string.isRequired, size: PropTypes.number }

function TypeIcon({ type, size = 16 }) {
  const { Icon } = TYPE_META[type] ?? TYPE_META.text
  return <Icon size={size} />
}

// ─── Lesson content components ───────────────────────────────────────────────

const lessonShape = PropTypes.shape({
  id:          PropTypes.number,
  title:       PropTypes.string,
  content:     PropTypes.string,
  quiz_data:   PropTypes.array,
  lesson_type: PropTypes.string,
})

VideoLesson.propTypes   = { lesson: lessonShape.isRequired }
function VideoLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      <div className="lp-video-player">
        <Video size={48} className="lp-video-icon" />
        <p className="lp-video-label">Video Player</p>
        {lesson.content && <p className="lp-video-url">{lesson.content}</p>}
      </div>
    </div>
  )
}

TextLesson.propTypes       = { lesson: lessonShape.isRequired }
function TextLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      {lesson.content ? (
        <div className="lp-text-body">
          <p className="lp-text-content">{lesson.content}</p>
        </div>
      ) : (
        <p className="lp-empty">No content yet.</p>
      )}
    </div>
  )
}

ImageLesson.propTypes      = { lesson: lessonShape.isRequired }
function ImageLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      {lesson.content
        ? <img src={lesson.content} alt={lesson.title} className="lp-image" />
        : (
          <div className="lp-video-player">
            <Image size={48} className="lp-video-icon" />
            <p className="lp-video-label">Image</p>
            {lesson.content && <p className="lp-video-url">{lesson.content}</p>}
          </div>
        )
      }
    </div>
  )
}

PdfLesson.propTypes        = { lesson: lessonShape.isRequired }
function PdfLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      <div className="lp-video-player">
        <FileIcon size={48} className="lp-video-icon" />
        <p className="lp-video-label">PDF Document</p>
        {lesson.content && (
          <a href={lesson.content} target="_blank" rel="noreferrer" className="lp-pdf-link">
            Open PDF ↗
          </a>
        )}
      </div>
    </div>
  )
}

AssignmentLesson.propTypes = { lesson: lessonShape.isRequired }
function AssignmentLesson({ lesson }) {
  return (
    <div className="lp-content-card">
      <div className="lp-assignment-body">
        <h3 className="lp-assignment-heading">Instructions</h3>
        <p className="lp-text-content">{lesson.content || 'No instructions provided.'}</p>
      </div>
    </div>
  )
}

QuizLesson.propTypes = {
  lesson:     lessonShape.isRequired,
  onComplete: PropTypes.func.isRequired,
}
function QuizLesson({ lesson, onComplete }) {
  const questions = lesson.quiz_data ?? []
  const [currentIdx, setCurrentIdx] = useState(0)
  // answers: { [questionIdx]: optionIdx }
  const [answers, setAnswers] = useState({})
  // revealed: set of question indices whose answer has been shown
  const [revealed, setRevealed] = useState(new Set())

  // State resets automatically because LessonContent passes key={lesson.id} to this component

  if (questions.length === 0) {
    return <div className="lp-content-card"><p className="lp-empty">No questions yet.</p></div>
  }

  const q = questions[currentIdx]
  const isLastQuestion = currentIdx === questions.length - 1
  const isAnswerRevealed = revealed.has(currentIdx)

  const handleSelect = (optionIdx) => {
    if (isAnswerRevealed) return           // lock after reveal
    const next = { ...answers, [currentIdx]: optionIdx }
    setAnswers(next)
    const nextRevealed = new Set(revealed)
    nextRevealed.add(currentIdx)
    setRevealed(nextRevealed)

    if (isLastQuestion) {
      // Small delay so the teacher sees the feedback before completion fires
      setTimeout(() => onComplete(), 800)
    } else {
      // Auto-advance after a short pause so teacher sees the feedback
      setTimeout(() => setCurrentIdx(i => i + 1), 900)
    }
  }

  const getOptionState = (optionIdx) => {
    if (!isAnswerRevealed) return ''
    const opt = q.options[optionIdx]
    if (opt.is_correct) return 'lp-option--correct'
    if (answers[currentIdx] === optionIdx) return 'lp-option--wrong'
    return 'lp-option--dimmed'
  }

  return (
    <div className="lp-content-card lp-quiz-card">
      <div className="lp-question-block">
        <p className="lp-question-counter">Question {currentIdx + 1} of {questions.length}</p>
        <p className="lp-question-text">{q.question}</p>
      </div>

      <div className="lp-options">
        {(q.options ?? []).map((opt, i) => (
          <button
            key={i}
            className={`lp-option lp-option--btn ${getOptionState(i)}`}
            onClick={() => handleSelect(i)}
            disabled={isAnswerRevealed}
          >
            <span className="lp-option-radio" />
            <span>{opt.text}</span>
            {isAnswerRevealed && opt.is_correct && (
              <span className="lp-option-badge lp-option-badge--correct">✓ Correct</span>
            )}
            {isAnswerRevealed && !opt.is_correct && answers[currentIdx] === i && (
              <span className="lp-option-badge lp-option-badge--wrong">✗ Incorrect</span>
            )}
          </button>
        ))}
      </div>

      {isAnswerRevealed && !isLastQuestion && (
        <div className="lp-quiz-nav">
          <button
            className="lp-quiz-arrow lp-quiz-arrow--next"
            onClick={() => setCurrentIdx(i => i + 1)}
          >
            Next question →
          </button>
        </div>
      )}
    </div>
  )
}

LessonContent.propTypes = {
  lesson:     lessonShape.isRequired,
  onComplete: PropTypes.func.isRequired,
}
function LessonContent({ lesson, onComplete }) {
  switch (lesson.lesson_type) {
    case 'video':      return <VideoLesson lesson={lesson} />
    case 'text':       return <TextLesson lesson={lesson} />
    case 'image':      return <ImageLesson lesson={lesson} />
    case 'pdf':        return <PdfLesson lesson={lesson} />
    case 'assignment': return <AssignmentLesson lesson={lesson} />
    case 'quiz':       return <QuizLesson key={lesson.id} lesson={lesson} onComplete={onComplete} />
    default:           return <TextLesson lesson={lesson} />
  }
}

// ─── Redirect component (/courses/:id/learn) ─────────────────────────────────

export function LearnRedirect() {
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
      .catch(() => setError('Could not load course.'))
  }, [id, navigate, user])

  if (error) return <p className="page-error">{error}</p>
  return <p className="page-loading">Loading…</p>
}

// ─── Main LessonPage ──────────────────────────────────────────────────────────

export default function LessonPage() {
  const { courseId, lessonId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [courseLearn, setCourseLearn] = useState(null)
  const [lesson, setLesson] = useState(null)
  const [note, setNote] = useState('')
  const [completing, setCompleting] = useState(false)
  const [error, setError] = useState('')

  // Redirect if not logged in
  useEffect(() => {
    if (!user) navigate('/login', { replace: true })
  }, [user, navigate])

  // Fetch sidebar structure whenever courseId changes
  useEffect(() => {
    client.get(`/courses/${courseId}/learn/`)
      .then(res => setCourseLearn(res.data))
      .catch(() => setError('Failed to load course.'))
  }, [courseId])

  // Fetch lesson whenever lessonId changes
  useEffect(() => {
    setLesson(null)
    client.get(`/courses/${courseId}/lessons/${lessonId}/`)
      .then(res => setLesson(res.data))
      .catch(() => setError('Failed to load lesson.'))
  }, [courseId, lessonId])

  // Reset note when lesson changes
  useEffect(() => { setNote('') }, [lessonId])

  const markComplete = useCallback(async () => {
    if (completing || lesson?.is_completed) return
    setCompleting(true)
    try {
      const res = await client.post(`/courses/${courseId}/lessons/${lessonId}/complete/`)
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
    } finally {
      setCompleting(false)
    }
  }, [completing, lesson, courseId, lessonId])

  const goTo = (id) => id && navigate(`/courses/${courseId}/learn/${id}`)

  if (error) return <p className="page-error">{error}</p>

  const typeMeta = lesson ? (TYPE_META[lesson.lesson_type] ?? TYPE_META.text) : null

  return (
    <div className="lp-page">

      {/* Top bar */}
      <div className="lp-topbar">
        <button className="lp-back" onClick={() => navigate(`/courses/${courseId}`)}>
          <ArrowLeft size={15} /> Back to Course
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
                Module {mod.order} — {mod.title}
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
                      <span className="lp-sidebar-lesson-dur">{lsn.duration_minutes} min</span>
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
                <span>Progress</span>
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
            <p className="page-loading">Loading lesson…</p>
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
              <LessonContent lesson={lesson} onComplete={markComplete} />

              {/* Navigation */}
              <div className="lp-nav">
                <button
                  className="lp-nav-btn"
                  disabled={!lesson.prev_lesson_id}
                  onClick={() => goTo(lesson.prev_lesson_id)}
                >
                  &#8249; Previous
                </button>

                {/* Hide Mark Complete for quizzes — they auto-complete on last answer */}
                {lesson.lesson_type !== 'quiz' && (
                  <button
                    className={`lp-complete-btn ${lesson.is_completed ? 'lp-complete-btn--done' : ''}`}
                    onClick={markComplete}
                    disabled={completing || lesson.is_completed}
                  >
                    {lesson.is_completed ? '✓ Completed' : completing ? 'Saving…' : 'Mark Complete'}
                  </button>
                )}
                {lesson.lesson_type === 'quiz' && lesson.is_completed && (
                  <span className="lp-complete-btn lp-complete-btn--done">✓ Completed</span>
                )}

                <button
                  className="lp-nav-btn lp-nav-btn--primary"
                  disabled={!lesson.next_lesson_id}
                  onClick={() => goTo(lesson.next_lesson_id)}
                >
                  Next &#8250;
                </button>
              </div>

              {/* Notes */}
              <div className="lp-notes">
                <h3 className="lp-notes-title">Your Notes</h3>
                <textarea
                  className="lp-notes-input"
                  placeholder="Add personal notes for this lesson…"
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
