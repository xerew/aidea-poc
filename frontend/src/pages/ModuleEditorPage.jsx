import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import {
  ArrowLeft, FileText, Video, Image, HelpCircle, FileDown, ClipboardList,
  Trash2, GripVertical, Save, Lock, Plus,
} from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { VideoEmbed, PdfEmbed } from '../components/lesson/MediaEmbeds'
import './ModuleEditorPage.css'

// ── Lesson type config ────────────────────────────────────────────────────────

const LESSON_TYPES = [
  { type: 'text',       label: 'Text',       Icon: FileText,     color: 'blue'   },
  { type: 'video',      label: 'Video',      Icon: Video,        color: 'purple' },
  { type: 'image',      label: 'Image',      Icon: Image,        color: 'green'  },
  { type: 'quiz',       label: 'Quiz',       Icon: HelpCircle,   color: 'yellow' },
  { type: 'pdf',        label: 'PDF',        Icon: FileDown,     color: 'red'    },
  { type: 'assignment', label: 'Assignment', Icon: ClipboardList, color: 'indigo' },
]

function lessonTypeConfig(type) {
  return LESSON_TYPES.find((t) => t.type === type) ?? LESSON_TYPES[0]
}

// ── Lesson icon ───────────────────────────────────────────────────────────────

function LessonTypeIcon({ type, size = 16 }) {
  const { Icon, color } = lessonTypeConfig(type)
  return <Icon size={size} className={`lesson-type-icon lesson-type-icon--${color}`} />
}

LessonTypeIcon.propTypes = { type: PropTypes.string.isRequired, size: PropTypes.number }

// ── Lesson editor panel ───────────────────────────────────────────────────────

// ── Quiz builder ──────────────────────────────────────────────────────────────

function emptyQuestion() {
  return {
    question: '',
    options: [
      { text: '', is_correct: false },
      { text: '', is_correct: false },
      { text: '', is_correct: false },
      { text: '', is_correct: false },
    ],
  }
}

function QuizBuilder({ quizData, locked, onChange }) {
  const questions = quizData ?? []

  const updateQuestion = (qi, text) => {
    const next = questions.map((q, i) => (i === qi ? { ...q, question: text } : q))
    onChange(next)
  }

  const updateOptionText = (qi, oi, text) => {
    const next = questions.map((q, i) =>
      i === qi
        ? { ...q, options: q.options.map((o, j) => (j === oi ? { ...o, text } : o)) }
        : q,
    )
    onChange(next)
  }

  const toggleCorrect = (qi, oi) => {
    const next = questions.map((q, i) =>
      i === qi
        ? { ...q, options: q.options.map((o, j) => (j === oi ? { ...o, is_correct: !o.is_correct } : o)) }
        : q,
    )
    onChange(next)
  }

  const addOption = (qi) => {
    const next = questions.map((q, i) =>
      i === qi ? { ...q, options: [...q.options, { text: '', is_correct: false }] } : q,
    )
    onChange(next)
  }

  const removeOption = (qi, oi) => {
    const next = questions.map((q, i) =>
      i === qi ? { ...q, options: q.options.filter((_, j) => j !== oi) } : q,
    )
    onChange(next)
  }

  const addQuestion = () => onChange([...questions, emptyQuestion()])

  const removeQuestion = (qi) => onChange(questions.filter((_, i) => i !== qi))

  return (
    <div className="quiz-builder">
      <h3 className="quiz-builder-title">Quiz Builder</h3>

      {questions.map((q, qi) => (
        <div key={qi} className="quiz-question">
          <div className="quiz-question-header">
            <input
              className="quiz-question-input"
              value={q.question}
              disabled={locked}
              onChange={(e) => updateQuestion(qi, e.target.value)}
              placeholder={`Question ${qi + 1}`}
            />
            {!locked && questions.length > 1 && (
              <button
                className="icon-btn icon-btn--danger"
                onClick={() => removeQuestion(qi)}
                title="Remove question"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>

          <div className="quiz-options">
            {q.options.map((opt, oi) => (
              <div key={oi} className="quiz-option">
                <input
                  type="checkbox"
                  className="quiz-option-checkbox"
                  checked={opt.is_correct}
                  disabled={locked}
                  onChange={() => toggleCorrect(qi, oi)}
                  title="Mark as correct answer"
                />
                <input
                  className="quiz-option-input"
                  value={opt.text}
                  disabled={locked}
                  onChange={(e) => updateOptionText(qi, oi, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + oi)}`}
                />
                {!locked && q.options.length > 2 && (
                  <button
                    className="icon-btn icon-btn--danger quiz-option-remove"
                    onClick={() => removeOption(qi, oi)}
                    title="Remove option"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {!locked && (
            <button className="quiz-add-option-btn" onClick={() => addOption(qi)}>
              <Plus size={13} /> Add Option
            </button>
          )}
        </div>
      ))}

      {!locked && (
        <button className="quiz-add-question-btn" onClick={addQuestion}>
          <Plus size={14} /> Add Question
        </button>
      )}
    </div>
  )
}

QuizBuilder.propTypes = {
  quizData: PropTypes.arrayOf(PropTypes.shape({
    question: PropTypes.string,
    options: PropTypes.arrayOf(PropTypes.shape({
      text: PropTypes.string,
      is_correct: PropTypes.bool,
    })),
  })).isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
}

// ── Lesson shape ──────────────────────────────────────────────────────────────

const lessonShape = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  lesson_type: PropTypes.string.isRequired,
  content: PropTypes.string,
  quiz_data: PropTypes.array,
  duration_minutes: PropTypes.number,
  is_required: PropTypes.bool,
  isDirty: PropTypes.bool,
  saving: PropTypes.bool,
})

function FieldError({ msg }) {
  if (!msg) return null
  return <p className="lesson-field-error">{msg}</p>
}

FieldError.propTypes = { msg: PropTypes.string }

// ── Lesson preview ────────────────────────────────────────────────────────────

LessonPreview.propTypes = { lesson: lessonShape.isRequired }

function LessonPreview({ lesson }) {
  switch (lesson.lesson_type) {
    case 'text':
      return lesson.content
        ? <p className="lesson-preview-text">{lesson.content}</p>
        : <p className="lesson-preview-empty">Write content above to see the preview.</p>
    case 'video':
      return lesson.content
        ? <VideoEmbed url={lesson.content} />
        : <p className="lesson-preview-empty">Paste a video URL above to see the preview.</p>
    case 'pdf':
      return lesson.content
        ? <PdfEmbed url={lesson.content} />
        : <p className="lesson-preview-empty">Paste a PDF URL above to see the preview.</p>
    case 'image':
      return lesson.content
        ? <img src={lesson.content} alt={lesson.title} className="lesson-preview-image" />
        : <p className="lesson-preview-empty">Paste an image URL above to see the preview.</p>
    case 'assignment':
      return lesson.content
        ? (
          <div>
            <h4 className="lesson-preview-subheading">Instructions</h4>
            <p className="lesson-preview-text">{lesson.content}</p>
          </div>
        )
        : <p className="lesson-preview-empty">Write instructions above to see the preview.</p>
    case 'quiz': {
      const first = (lesson.quiz_data ?? [])[0]
      if (!first?.question) return <p className="lesson-preview-empty">Add a question to see the preview.</p>
      return (
        <div>
          <p className="lesson-preview-quiz-q">{first.question}</p>
          <ul className="lesson-preview-quiz-opts">
            {first.options.filter(o => o.text).map((o, i) => <li key={i}>{o.text}</li>)}
          </ul>
        </div>
      )
    }
    default:
      return null
  }
}

function LessonEditor({ lesson, locked, onChange, onDelete, onSave, errors }) {
  const cfg = lessonTypeConfig(lesson.lesson_type)
  const err = errors ?? {}

  return (
    <div className="lesson-editor-panel">
      <div className="lesson-editor-header">
        <div className="lesson-editor-header-left">
          <div className={`lesson-editor-icon-wrap lesson-editor-icon-wrap--${cfg.color}`}>
            <cfg.Icon size={20} />
          </div>
          <div>
            <span className="lesson-editor-editing-label">Editing {cfg.label}</span>
            <h2 className="lesson-editor-title">Lesson Editor</h2>
          </div>
        </div>
        {!locked && (
          <button
            className="icon-btn icon-btn--danger"
            onClick={onDelete}
            title="Delete lesson"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div className="lesson-editor-body">
        <div className="lesson-field">
          <label className="lesson-field-label">Lesson Title</label>
          <input
            className={`lesson-field-input${err.title ? ' lesson-field-input--error' : ''}`}
            value={lesson.title}
            disabled={locked}
            onChange={(e) => onChange('title', e.target.value)}
            placeholder="New Text"
          />
          <FieldError msg={err.title} />
        </div>

        <div className="lesson-field">
          <label className="lesson-field-label">Description</label>
          <textarea
            className="lesson-field-textarea"
            value={lesson.description}
            disabled={locked}
            rows={3}
            onChange={(e) => onChange('description', e.target.value)}
            placeholder="Describe what students will learn…"
          />
        </div>

        {lesson.lesson_type === 'text' && (
          <div className="lesson-field">
            <label className="lesson-field-label">Content</label>
            <textarea
              className="lesson-field-textarea lesson-field-textarea--content"
              value={lesson.content}
              disabled={locked}
              rows={8}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder="Write your lesson content here…"
            />
            <p className="lesson-field-hint">Supports markdown formatting</p>
          </div>
        )}

        {['video', 'image', 'pdf'].includes(lesson.lesson_type) && (
          <div className="lesson-field">
            <label className="lesson-field-label">
              {lesson.lesson_type === 'video' ? 'Video URL' : lesson.lesson_type === 'image' ? 'Image URL' : 'PDF URL'}
            </label>
            <input
              type="url"
              className={`lesson-field-input${err.content ? ' lesson-field-input--error' : ''}`}
              value={lesson.content}
              disabled={locked}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder="https://…"
            />
            <FieldError msg={err.content} />
          </div>
        )}

        {lesson.lesson_type === 'assignment' && (
          <div className="lesson-field">
            <label className="lesson-field-label">Assignment Instructions</label>
            <textarea
              className={`lesson-field-textarea lesson-field-textarea--content${err.content ? ' lesson-field-textarea--error' : ''}`}
              value={lesson.content}
              disabled={locked}
              rows={6}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder="Write the assignment instructions here…"
            />
            <FieldError msg={err.content} />
            <p className="lesson-field-hint">Supports markdown formatting</p>
          </div>
        )}

        {lesson.lesson_type === 'quiz' && (
          <>
            <FieldError msg={err.quiz_data} />
            <QuizBuilder
              quizData={lesson.quiz_data ?? []}
              locked={locked}
              onChange={(next) => onChange('quiz_data', next)}
            />
          </>
        )}

        <div className="lesson-field">
          <label className="lesson-field-label">Duration (estimated)</label>
          <input
            className="lesson-field-input lesson-field-input--short"
            value={lesson.duration_minutes || ''}
            disabled={locked}
            type="number"
            min={0}
            onChange={(e) => onChange('duration_minutes', Number(e.target.value))}
            placeholder="e.g., 15 min"
          />
        </div>

        <div className="lesson-field">
          <label className="lesson-required-label">
            <input
              type="checkbox"
              checked={lesson.is_required}
              disabled={locked}
              onChange={(e) => onChange('is_required', e.target.checked)}
            />
            <div>
              <span className="lesson-required-title">Required lesson</span>
              <span className="lesson-required-sub">Students must complete this to progress</span>
            </div>
          </label>
        </div>

        <FieldError msg={err.general} />

        {!locked && lesson.isDirty && (
          <button
            className="lesson-save-btn"
            onClick={onSave}
            disabled={lesson.saving}
          >
            <Save size={15} />
            {lesson.saving ? 'Saving…' : 'Save Lesson'}
          </button>
        )}

        <div className="lesson-preview-card">
          <h3 className="lesson-preview-title">Preview</h3>
          <p className="lesson-preview-sub">How this lesson will appear to students</p>
          <div className="lesson-preview-body">
            <LessonPreview lesson={lesson} />
          </div>
        </div>
      </div>
    </div>
  )
}

LessonEditor.propTypes = {
  lesson: lessonShape.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  errors: PropTypes.object,
}

// ── Validation ────────────────────────────────────────────────────────────────

function validateLesson(lesson) {
  const errors = {}
  if (!lesson.title.trim()) {
    errors.title = 'Lesson title is required.'
  }
  if (['video', 'image', 'pdf'].includes(lesson.lesson_type) && !lesson.content.trim()) {
    const label = lesson.lesson_type === 'video' ? 'Video' : lesson.lesson_type === 'image' ? 'Image' : 'PDF'
    errors.content = `${label} URL is required.`
  }
  if (lesson.lesson_type === 'assignment' && !lesson.content.trim()) {
    errors.content = 'Assignment instructions are required.'
  }
  if (lesson.lesson_type === 'quiz' && (!lesson.quiz_data || lesson.quiz_data.length === 0)) {
    errors.quiz_data = 'At least one question is required.'
  }
  return Object.keys(errors).length ? errors : null
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ModuleEditorPage() {
  const { id: courseId, moduleId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [module, setModule] = useState(null)
  const [isPublished, setIsPublished] = useState(false)
  const [courseAuthorId, setCourseAuthorId] = useState(null)
  const [lessons, setLessons] = useState([])
  const [selectedLessonId, setSelectedLessonId] = useState(null)
  const [moduleForm, setModuleForm] = useState({ title: '', description: '' })
  const [moduleDirty, setModuleDirty] = useState(false)
  const [moduleSaving, setModuleSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [error, setError] = useState('')
  const [lessonErrors, setLessonErrors] = useState({})

  // drag-and-drop state
  const [dragId, setDragId] = useState(null)
  const [dragOverId, setDragOverId] = useState(null)

  useEffect(() => {
    Promise.all([
      client.get(`/authoring/courses/${courseId}/modules/${moduleId}/edit/`),
      client.get(`/authoring/courses/${courseId}/`),
    ])
      .then(([modRes, courseRes]) => {
        const m = modRes.data
        setModule(m)
        setModuleForm({ title: m.title, description: m.description })
        setLessons(m.lessons.map((l) => ({ ...l, isDirty: false, isNew: false, saving: false })))
        setIsPublished(courseRes.data.is_published)
        setCourseAuthorId(courseRes.data.created_by_id)
      })
      .catch(() => setError('Failed to load module.'))
  }, [courseId, moduleId])

  const selectedLesson = lessons.find((l) => l.id === selectedLessonId) ?? null

  // ── Module fields ─────────────────────────────────────────────────────────

  const handleModuleFieldChange = (field, value) => {
    setModuleForm((f) => ({ ...f, [field]: value }))
    setModuleDirty(true)
  }

  const saveModuleFields = async () => {
    setModuleSaving(true)
    setSaveStatus('')
    try {
      await client.patch(`/authoring/courses/${courseId}/modules/${moduleId}/`, moduleForm)
      setModuleDirty(false)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus(''), 3000)
    } catch {
      setSaveStatus('error')
    } finally {
      setModuleSaving(false)
    }
  }

  // ── Lesson helpers ────────────────────────────────────────────────────────

  const addLesson = async (lessonType) => {
    const tempId = `new-${Date.now()}`
    const label = lessonTypeConfig(lessonType).label
    const newLesson = {
      id: tempId,
      title: `New ${label}`,
      description: '',
      lesson_type: lessonType,
      content: '',
      quiz_data: lessonType === 'quiz' ? [emptyQuestion()] : [],
      duration_minutes: 0,
      order: lessons.length + 1,
      is_required: true,
      isDirty: true,
      isNew: true,
      saving: false,
    }
    setLessons((ls) => [...ls, newLesson])
    setSelectedLessonId(tempId)
  }

  const saveLessonRequest = useCallback(async (lesson) => {
    const payload = {
      title: lesson.title,
      description: lesson.description,
      lesson_type: lesson.lesson_type,
      content: lesson.content,
      quiz_data: lesson.quiz_data ?? [],
      duration_minutes: lesson.duration_minutes,
      is_required: lesson.is_required,
    }
    if (lesson.isNew) {
      const res = await client.post(
        `/authoring/courses/${courseId}/modules/${moduleId}/lessons/`, payload,
      )
      return { tempId: lesson.id, saved: res.data }
    }
    const res = await client.patch(
      `/authoring/courses/${courseId}/modules/${moduleId}/lessons/${lesson.id}/`, payload,
    )
    return { tempId: lesson.id, saved: res.data }
  }, [courseId, moduleId])

  const saveLesson = async (lesson) => {
    const errors = validateLesson(lesson)
    if (errors) {
      setLessonErrors((prev) => ({ ...prev, [lesson.id]: errors }))
      return
    }
    setLessonErrors((prev) => { const next = { ...prev }; delete next[lesson.id]; return next })
    setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: true } : l)))
    try {
      const { tempId, saved } = await saveLessonRequest(lesson)
      setLessons((ls) =>
        ls.map((l) => (l.id === tempId ? { ...saved, isDirty: false, isNew: false, saving: false } : l))
      )
      setSelectedLessonId(saved.id)
      setLessonErrors((prev) => { const next = { ...prev }; delete next[tempId]; return next })
    } catch (err) {
      const detail = err.response?.data?.detail
        ?? Object.values(err.response?.data ?? {})[0]
        ?? 'Save failed. Please try again.'
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
      setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: false } : l)))
    }
  }

  const updateLessonField = (field, value) => {
    if (!selectedLessonId) return
    setLessons((ls) =>
      ls.map((l) => (l.id === selectedLessonId ? { ...l, [field]: value, isDirty: true } : l))
    )
    // clear validation error for this field on change
    setLessonErrors((prev) => {
      const errs = prev[selectedLessonId]
      if (!errs || !errs[field]) return prev
      const next = { ...errs }
      delete next[field]
      return { ...prev, [selectedLessonId]: next }
    })
  }

  const deleteLesson = async (lesson) => {
    if (lesson.isNew) {
      setLessons((ls) => ls.filter((l) => l.id !== lesson.id))
      setSelectedLessonId(null)
      return
    }
    try {
      await client.delete(
        `/authoring/courses/${courseId}/modules/${moduleId}/lessons/${lesson.id}/`,
      )
      setLessons((ls) => ls.filter((l) => l.id !== lesson.id))
      setSelectedLessonId(null)
    } catch (err) {
      const detail = err.response?.data?.detail ?? 'Delete failed. Please try again.'
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
    }
  }

  // ── Drag-and-drop (lessons) ───────────────────────────────────────────────

  const handleDragStart = (e, id) => {
    setDragId(id)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e, id) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (id !== dragOverId) setDragOverId(id)
  }

  const handleDrop = async (e, targetId) => {
    e.preventDefault()
    setDragOverId(null)
    if (!dragId || dragId === targetId) { setDragId(null); return }

    const fromIdx = lessons.findIndex((l) => l.id === dragId)
    const toIdx = lessons.findIndex((l) => l.id === targetId)
    const reordered = [...lessons]
    reordered.splice(fromIdx, 1)
    reordered.splice(toIdx, 0, lessons[fromIdx])
    setLessons(reordered)
    setDragId(null)

    // only persist if all lessons are saved (no unsaved temp IDs)
    const hasNew = reordered.some((l) => l.isNew)
    if (!hasNew) {
      try {
        await client.patch(
          `/authoring/courses/${courseId}/modules/${moduleId}/lessons/reorder/`,
          { order: reordered.map((l) => l.id) },
        )
      } catch { /* silent — visual order already updated */ }
    }
  }

  const handleDragEnd = () => {
    setDragId(null)
    setDragOverId(null)
  }

  if (error) return <p className="page-error">{error}</p>
  if (!module) return <p className="page-loading">Loading…</p>

  const isAuthor = courseAuthorId != null && user?.id === courseAuthorId
  const isAdmin = user?.profile?.user_type === 'admin'
  const locked = isPublished && !isAuthor && !isAdmin

  return (
    <div className="module-editor-page">

      {/* Top bar */}
      <div className="module-editor-topbar">
        <button className="back-link" onClick={() => navigate(`/authoring/courses/${courseId}`)}>
          <ArrowLeft size={15} /> Back to Course
        </button>

        <div className="module-editor-topbar-right">
          {saveStatus === 'saved' && <span className="save-msg save-msg--ok">Saved!</span>}
          {saveStatus === 'error' && <span className="save-msg save-msg--err">Save failed</span>}
          {!locked && moduleDirty && (
            <button
              className="me-save-btn"
              onClick={saveModuleFields}
              disabled={moduleSaving}
            >
              <Save size={15} />
              {moduleSaving ? 'Saving…' : 'Save'}
            </button>
          )}
          {isPublished && (
            <div className="published-banner">
              <Lock size={14} />
              {locked
                ? 'This course is published — only its author can edit it.'
                : 'This course is published — your edits go live immediately.'}
            </div>
          )}
        </div>
      </div>

      <h1 className="module-editor-heading">Module Editor</h1>

      <div className="module-editor-layout">

        {/* ── Left panel ── */}
        <aside className="module-editor-sidebar">

          <div className="me-card">
            <h2 className="me-card-title">Module Structure</h2>
            <label className="me-label">Module Title</label>
            <input
              className="me-input"
              value={moduleForm.title}
              disabled={locked}
              onChange={(e) => handleModuleFieldChange('title', e.target.value)}
              placeholder="Module title"
            />
            <label className="me-label" style={{ marginTop: '1rem' }}>Description</label>
            <textarea
              className="me-textarea"
              value={moduleForm.description}
              disabled={locked}
              rows={3}
              onChange={(e) => handleModuleFieldChange('description', e.target.value)}
              placeholder="Module overview…"
            />
          </div>

          {!locked && (
            <div className="me-card">
              <h2 className="me-card-title">Add Lesson/Activity</h2>
              <div className="me-lesson-type-grid">
                {LESSON_TYPES.map(({ type, label, Icon, color }) => (
                  <button
                    key={type}
                    className={`me-type-btn me-type-btn--${color}`}
                    onClick={() => addLesson(type)}
                  >
                    <Icon size={22} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="me-card">
            <h2 className="me-card-title">Lessons ({lessons.length})</h2>
            <ul className="me-lesson-list">
              {lessons.map((lesson, idx) => {
                const cfg = lessonTypeConfig(lesson.lesson_type)
                const isDragOver = dragOverId === lesson.id && dragId !== lesson.id
                return (
                  <li
                    key={lesson.id}
                    className={[
                      'me-lesson-item',
                      selectedLessonId === lesson.id ? 'me-lesson-item--active' : '',
                      dragId === lesson.id ? 'me-lesson-item--dragging' : '',
                      isDragOver ? 'me-lesson-item--drag-over' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => setSelectedLessonId(lesson.id)}
                    draggable={!locked}
                    onDragStart={(e) => handleDragStart(e, lesson.id)}
                    onDragOver={(e) => handleDragOver(e, lesson.id)}
                    onDrop={(e) => handleDrop(e, lesson.id)}
                    onDragEnd={handleDragEnd}
                  >
                    <GripVertical size={14} className="me-lesson-drag" />
                    <LessonTypeIcon type={lesson.lesson_type} size={15} />
                    <span className="me-lesson-title">{lesson.title || `New ${cfg.label}`}</span>
                    <span className="me-lesson-order">{idx + 1}</span>
                  </li>
                )
              })}
              {lessons.length === 0 && (
                <li className="me-lesson-empty">No lessons yet. Add one above.</li>
              )}
            </ul>
          </div>

        </aside>

        {/* ── Right panel ── */}
        <main className="module-editor-main">
          {selectedLesson ? (
            <LessonEditor
              lesson={selectedLesson}
              locked={locked}
              onChange={updateLessonField}
              onDelete={() => deleteLesson(selectedLesson)}
              onSave={() => saveLesson(selectedLesson)}
              errors={lessonErrors[selectedLesson.id]}
            />
          ) : (
            <div className="me-empty-state">
              <FileText size={40} className="me-empty-icon" />
              <p>Select a lesson from the list, or add a new one.</p>
            </div>
          )}
        </main>

      </div>
    </div>
  )
}
