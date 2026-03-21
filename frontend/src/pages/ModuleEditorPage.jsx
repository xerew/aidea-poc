import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import {
  ArrowLeft, FileText, Video, Image, HelpCircle, FileDown, ClipboardList,
  Trash2, GripVertical, Save, Lock,
} from 'lucide-react'
import client from '../api/client'
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

const lessonShape = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  lesson_type: PropTypes.string.isRequired,
  content: PropTypes.string,
  duration_minutes: PropTypes.number,
  is_required: PropTypes.bool,
  isDirty: PropTypes.bool,
  saving: PropTypes.bool,
})

function LessonEditor({ lesson, locked, onChange, onDelete, onSave }) {
  const cfg = lessonTypeConfig(lesson.lesson_type)

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
            className="lesson-field-input"
            value={lesson.title}
            disabled={locked}
            onChange={(e) => onChange('title', e.target.value)}
            placeholder="New Text"
          />
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
          <p className="lesson-preview-sub">Preview how this lesson will appear to students</p>
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
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ModuleEditorPage() {
  const { id: courseId, moduleId } = useParams()
  const navigate = useNavigate()

  const [module, setModule] = useState(null)
  const [isPublished, setIsPublished] = useState(false)
  const [lessons, setLessons] = useState([])
  const [selectedLessonId, setSelectedLessonId] = useState(null)
  const [moduleForm, setModuleForm] = useState({ title: '', description: '' })
  const [moduleDirty, setModuleDirty] = useState(false)
  const [moduleSaving, setModuleSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [error, setError] = useState('')

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
    setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: true } : l)))
    try {
      const { tempId, saved } = await saveLessonRequest(lesson)
      setLessons((ls) =>
        ls.map((l) => (l.id === tempId ? { ...saved, isDirty: false, isNew: false, saving: false } : l))
      )
      setSelectedLessonId(saved.id)
    } catch {
      setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: false } : l)))
    }
  }

  const updateLessonField = (field, value) => {
    if (!selectedLessonId) return
    setLessons((ls) =>
      ls.map((l) => (l.id === selectedLessonId ? { ...l, [field]: value, isDirty: true } : l))
    )
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
    } catch { /* user can retry */ }
  }

  if (error) return <p className="page-error">{error}</p>
  if (!module) return <p className="page-loading">Loading…</p>

  const locked = isPublished

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
          {locked && (
            <div className="published-banner">
              <Lock size={14} /> Published — read only
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
                return (
                  <li
                    key={lesson.id}
                    className={`me-lesson-item${selectedLessonId === lesson.id ? ' me-lesson-item--active' : ''}`}
                    onClick={() => setSelectedLessonId(lesson.id)}
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
