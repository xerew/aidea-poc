import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, FileText, Video, Image, HelpCircle, FileDown, ClipboardList,
  Trash2, GripVertical, Save, Lock, Plus, Upload,
} from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { VideoEmbed, PdfEmbed } from '../components/lesson/MediaEmbeds'
import TranslationBar from '../components/authoring/TranslationBar'
import './ModuleEditorPage.css'

// ── Lesson type config ────────────────────────────────────────────────────────

const LESSON_TYPES = [
  { type: 'text',       Icon: FileText,     color: 'blue'   },
  { type: 'video',      Icon: Video,        color: 'purple' },
  { type: 'image',      Icon: Image,        color: 'green'  },
  { type: 'quiz',       Icon: HelpCircle,   color: 'yellow' },
  { type: 'pdf',        Icon: FileDown,     color: 'red'    },
  { type: 'assignment', Icon: ClipboardList, color: 'indigo' },
]

function lessonTypeConfig(type) {
  return LESSON_TYPES.find((lt) => lt.type === type) ?? LESSON_TYPES[0]
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

// Merge a lesson's base quiz structure (is_correct + option/question order —
// always authoritative) with its translated text for `lang`. Falls back to
// blank text (not the source text) when nothing has been translated yet, so
// translated-mode inputs never masquerade untranslated source text as a
// translation.
function mergedQuizData(lesson, lang) {
  const base = lesson.quiz_data ?? []
  if (lang === 'original') return base
  const translated = lesson.translations?.[lang]?.quiz_data
  if (Array.isArray(translated) && translated.length === base.length) {
    return base.map((q, qi) => ({
      question: translated[qi]?.question ?? '',
      options: q.options.map((o, oi) => ({
        text: translated[qi]?.options?.[oi]?.text ?? '',
        is_correct: o.is_correct,
      })),
    }))
  }
  return base.map((q) => ({
    question: '',
    options: q.options.map((o) => ({ text: '', is_correct: o.is_correct })),
  }))
}

function QuizBuilder({ quizData, textDisabled, structureLocked, onChange }) {
  const { t } = useTranslation()
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
      <h3 className="quiz-builder-title">{t('authoring.moduleEditor.quizBuilderTitle')}</h3>

      {questions.map((q, qi) => (
        <div key={qi} className="quiz-question">
          <div className="quiz-question-header">
            <input
              className="quiz-question-input"
              value={q.question}
              disabled={textDisabled}
              onChange={(e) => updateQuestion(qi, e.target.value)}
              placeholder={t('authoring.moduleEditor.questionPlaceholder', { number: qi + 1 })}
            />
            {!structureLocked && questions.length > 1 && (
              <button
                className="icon-btn icon-btn--danger"
                onClick={() => removeQuestion(qi)}
                title={t('authoring.moduleEditor.removeQuestion')}
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
                  disabled={structureLocked}
                  onChange={() => toggleCorrect(qi, oi)}
                  title={t('authoring.moduleEditor.markCorrect')}
                />
                <input
                  className="quiz-option-input"
                  value={opt.text}
                  disabled={textDisabled}
                  onChange={(e) => updateOptionText(qi, oi, e.target.value)}
                  placeholder={t('authoring.moduleEditor.optionPlaceholder', { letter: String.fromCharCode(65 + oi) })}
                />
                {!structureLocked && q.options.length > 2 && (
                  <button
                    className="icon-btn icon-btn--danger quiz-option-remove"
                    onClick={() => removeOption(qi, oi)}
                    title={t('authoring.moduleEditor.removeOption')}
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {!structureLocked && (
            <button className="quiz-add-option-btn" onClick={() => addOption(qi)}>
              <Plus size={13} /> {t('authoring.moduleEditor.addOption')}
            </button>
          )}
        </div>
      ))}

      {!structureLocked && (
        <button className="quiz-add-question-btn" onClick={addQuestion}>
          <Plus size={14} /> {t('authoring.moduleEditor.addQuestion')}
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
  textDisabled: PropTypes.bool.isRequired,
  structureLocked: PropTypes.bool.isRequired,
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
  isNew: PropTypes.bool,
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
  const { t } = useTranslation()
  switch (lesson.lesson_type) {
    case 'text':
      return lesson.content
        ? <p className="lesson-preview-text">{lesson.content}</p>
        : <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewTextEmpty')}</p>
    case 'video':
      return lesson.content
        ? <VideoEmbed url={lesson.content} />
        : <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewVideoEmpty')}</p>
    case 'pdf':
      return lesson.content
        ? <PdfEmbed url={lesson.content} />
        : <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewPdfEmpty')}</p>
    case 'image':
      return lesson.content
        ? <img src={lesson.content} alt={lesson.title} className="lesson-preview-image" />
        : <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewImageEmpty')}</p>
    case 'assignment':
      return lesson.content
        ? (
          <div>
            <h4 className="lesson-preview-subheading">{t('lesson.assignment.instructions')}</h4>
            <p className="lesson-preview-text">{lesson.content}</p>
          </div>
        )
        : <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewAssignmentEmpty')}</p>
    case 'quiz': {
      const first = (lesson.quiz_data ?? [])[0]
      if (!first?.question) return <p className="lesson-preview-empty">{t('authoring.moduleEditor.previewQuizEmpty')}</p>
      return (
        <div>
          <p className="lesson-preview-quiz-q">{first.question}</p>
          <ul className="lesson-preview-quiz-opts">
            {(first.options ?? []).filter(o => o.text).map((o, i) => <li key={i}>{o.text}</li>)}
          </ul>
        </div>
      )
    }
    default:
      return null
  }
}

function LessonEditor({ lesson, locked, translating, onChange, onDelete, onSave, onError, errors }) {
  const { t } = useTranslation()
  const cfg = lessonTypeConfig(lesson.lesson_type)
  const typeLabel = t(`lesson.type.${lesson.lesson_type}`)
  const err = errors ?? {}
  const [uploading, setUploading] = useState(false)

  // A brand-new, not-yet-saved lesson has no `translations` bucket to write
  // into — block translated-mode edits on it until it's saved in the
  // original language.
  const blockedNew = lesson.isNew && translating
  const fieldsDisabled = locked || blockedNew
  const structureLocked = locked || translating

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/upload/', fd)
      onChange('content', res.data.url)
      onError(null)
    } catch (uploadErr) {
      onError(uploadErr.response?.data?.error ?? t('authoring.moduleEditor.uploadFailed'))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="lesson-editor-panel">
      <div className="lesson-editor-header">
        <div className="lesson-editor-header-left">
          <div className={`lesson-editor-icon-wrap lesson-editor-icon-wrap--${cfg.color}`}>
            <cfg.Icon size={20} />
          </div>
          <div>
            <span className="lesson-editor-editing-label">{t('authoring.moduleEditor.editingLabel', { label: typeLabel })}</span>
            <h2 className="lesson-editor-title">{t('authoring.moduleEditor.lessonEditorTitle')}</h2>
          </div>
        </div>
        {!locked && !translating && (
          <button
            className="icon-btn icon-btn--danger"
            onClick={onDelete}
            title={t('authoring.moduleEditor.deleteLesson')}
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div className="lesson-editor-body">
        {blockedNew && <p className="lesson-field-hint">{t('authoring.translate.saveOriginalFirst')}</p>}

        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.lessonTitleLabel')}</label>
          <input
            className={`lesson-field-input${err.title ? ' lesson-field-input--error' : ''}`}
            value={lesson.title}
            disabled={fieldsDisabled}
            onChange={(e) => onChange('title', e.target.value)}
            placeholder={t('authoring.moduleEditor.titlePlaceholderExample')}
          />
          <FieldError msg={err.title} />
        </div>

        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.descriptionLabel')}</label>
          <textarea
            className="lesson-field-textarea"
            value={lesson.description}
            disabled={fieldsDisabled}
            rows={3}
            onChange={(e) => onChange('description', e.target.value)}
            placeholder={t('authoring.moduleEditor.descPlaceholder')}
          />
        </div>

        {lesson.lesson_type === 'text' && (
          <div className="lesson-field">
            <label className="lesson-field-label">{t('authoring.moduleEditor.contentLabel')}</label>
            <textarea
              className="lesson-field-textarea lesson-field-textarea--content"
              value={lesson.content}
              disabled={fieldsDisabled}
              rows={8}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder={t('authoring.moduleEditor.contentPlaceholder')}
            />
            <p className="lesson-field-hint">{t('authoring.moduleEditor.markdownHint')}</p>
          </div>
        )}

        {['video', 'image', 'pdf'].includes(lesson.lesson_type) && (
          <div className="lesson-field">
            <label className="lesson-field-label">
              {t('authoring.moduleEditor.urlLabel', { type: typeLabel })}
            </label>
            <input
              type="url"
              className={`lesson-field-input${err.content ? ' lesson-field-input--error' : ''}`}
              value={lesson.content}
              disabled={fieldsDisabled}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder={t('authoring.moduleEditor.urlPlaceholder')}
            />
            <FieldError msg={err.content} />
            {['pdf', 'image'].includes(lesson.lesson_type) && !locked && !translating && (
              <div className="lesson-upload-row">
                <span className="lesson-upload-or">{t('authoring.moduleEditor.uploadOr')}</span>
                <label className="lesson-upload-btn">
                  <Upload size={14} />
                  {uploading ? t('authoring.moduleEditor.uploading') : t('authoring.moduleEditor.uploadFile')}
                  <input
                    type="file"
                    accept={lesson.lesson_type === 'pdf' ? '.pdf' : 'image/*'}
                    hidden
                    disabled={uploading}
                    onChange={handleFileUpload}
                  />
                </label>
              </div>
            )}
          </div>
        )}

        {lesson.lesson_type === 'assignment' && (
          <div className="lesson-field">
            <label className="lesson-field-label">{t('authoring.moduleEditor.assignmentInstructionsLabel')}</label>
            <textarea
              className={`lesson-field-textarea lesson-field-textarea--content${err.content ? ' lesson-field-textarea--error' : ''}`}
              value={lesson.content}
              disabled={fieldsDisabled}
              rows={6}
              onChange={(e) => onChange('content', e.target.value)}
              placeholder={t('authoring.moduleEditor.assignmentPlaceholder')}
            />
            <FieldError msg={err.content} />
            <p className="lesson-field-hint">{t('authoring.moduleEditor.markdownHint')}</p>
          </div>
        )}

        {lesson.lesson_type === 'quiz' && (
          <>
            <FieldError msg={err.quiz_data} />
            <QuizBuilder
              quizData={lesson.quiz_data ?? []}
              textDisabled={fieldsDisabled}
              structureLocked={structureLocked}
              onChange={(next) => onChange('quiz_data', next)}
            />
          </>
        )}

        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.durationLabel')}</label>
          <input
            className="lesson-field-input lesson-field-input--short"
            value={lesson.duration_minutes || ''}
            disabled={locked || translating}
            type="number"
            min={0}
            onChange={(e) => onChange('duration_minutes', Number(e.target.value))}
            placeholder={t('authoring.moduleEditor.durationPlaceholder')}
          />
        </div>

        <div className="lesson-field">
          <label className="lesson-required-label">
            <input
              type="checkbox"
              checked={lesson.is_required}
              disabled={locked || translating}
              onChange={(e) => onChange('is_required', e.target.checked)}
            />
            <div>
              <span className="lesson-required-title">{t('authoring.moduleEditor.requiredTitle')}</span>
              <span className="lesson-required-sub">{t('authoring.moduleEditor.requiredSub')}</span>
            </div>
          </label>
        </div>

        <FieldError msg={err.general} />

        {!locked && !blockedNew && lesson.isDirty && (
          <button
            className="lesson-save-btn"
            onClick={onSave}
            disabled={lesson.saving}
          >
            <Save size={15} />
            {lesson.saving ? t('authoring.moduleEditor.savingLesson') : t('authoring.moduleEditor.saveLesson')}
          </button>
        )}

        <div className="lesson-preview-card">
          <h3 className="lesson-preview-title">{t('authoring.moduleEditor.previewTitle')}</h3>
          <p className="lesson-preview-sub">{t('authoring.moduleEditor.previewSub')}</p>
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
  translating: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  onError: PropTypes.func.isRequired,
  errors: PropTypes.object,
}

// ── Validation ────────────────────────────────────────────────────────────────

function validateLesson(lesson, t) {
  const errors = {}
  if (!lesson.title.trim()) {
    errors.title = t('authoring.moduleEditor.titleRequiredError')
  }
  if (['video', 'image', 'pdf'].includes(lesson.lesson_type) && !lesson.content.trim()) {
    errors.content = t('authoring.moduleEditor.urlRequiredError', { type: t(`lesson.type.${lesson.lesson_type}`) })
  }
  if (lesson.lesson_type === 'assignment' && !lesson.content.trim()) {
    errors.content = t('authoring.moduleEditor.assignmentRequiredError')
  }
  if (lesson.lesson_type === 'quiz' && (!lesson.quiz_data || lesson.quiz_data.length === 0)) {
    errors.quiz_data = t('authoring.moduleEditor.quizRequiredError')
  }
  return Object.keys(errors).length ? errors : null
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ModuleEditorPage() {
  const { t } = useTranslation()
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

  // ── Translation state ──────────────────────────────────────────────────────
  const [activeLang, setActiveLang] = useState('original')
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [translationStatus, setTranslationStatus] = useState({})
  const translating = activeLang !== 'original'

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
        setSourceLanguage(courseRes.data.source_language ?? 'en')
        setTranslationStatus(courseRes.data.translation_status ?? {})
      })
      .catch(() => setError(t('authoring.moduleEditor.loadError')))
  }, [courseId, moduleId, t])

  const selectedLesson = lessons.find((l) => l.id === selectedLessonId) ?? null
  const displayLesson = selectedLesson && translating
    ? {
        ...selectedLesson,
        title: selectedLesson.translations?.[activeLang]?.title ?? '',
        description: selectedLesson.translations?.[activeLang]?.description ?? '',
        content: selectedLesson.translations?.[activeLang]?.content ?? '',
        quiz_data: mergedQuizData(selectedLesson, activeLang),
      }
    : selectedLesson

  // ── Module fields ─────────────────────────────────────────────────────────

  const moduleFieldValue = (field) =>
    (activeLang === 'original' ? moduleForm[field] : (module?.translations?.[activeLang]?.[field] ?? ''))

  const handleModuleFieldChange = (field, value) => {
    if (activeLang === 'original') {
      setModuleForm((f) => ({ ...f, [field]: value }))
    } else {
      setModule((m) => ({
        ...m,
        translations: { ...m.translations, [activeLang]: { ...(m.translations?.[activeLang] ?? {}), [field]: value } },
      }))
    }
    setModuleDirty(true)
  }

  const saveModuleFields = async () => {
    setModuleSaving(true)
    setSaveStatus('')
    try {
      if (activeLang === 'original') {
        await client.patch(`/authoring/courses/${courseId}/modules/${moduleId}/`, moduleForm)
      } else {
        const payload = {
          title: module.translations?.[activeLang]?.title ?? '',
          description: module.translations?.[activeLang]?.description ?? '',
        }
        const res = await client.patch(`/authoring/courses/${courseId}/modules/${moduleId}/?lang=${activeLang}`, payload)
        setModule((m) => ({ ...m, translations: res.data.translations }))
      }
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
    const newLesson = {
      id: tempId,
      title: t('authoring.moduleEditor.newLessonTitle', { type: t(`lesson.type.${lessonType}`) }),
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
    if (activeLang === 'original') {
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
    }

    const payload = {
      title: lesson.translations?.[activeLang]?.title ?? '',
      description: lesson.translations?.[activeLang]?.description ?? '',
      content: lesson.translations?.[activeLang]?.content ?? '',
    }
    if (lesson.lesson_type === 'quiz') {
      payload.quiz_data = mergedQuizData(lesson, activeLang)
    }
    const res = await client.patch(
      `/authoring/courses/${courseId}/modules/${moduleId}/lessons/${lesson.id}/?lang=${activeLang}`, payload,
    )
    return { tempId: lesson.id, saved: res.data }
  }, [courseId, moduleId, activeLang])

  const saveLesson = async (lesson) => {
    if (lesson.isNew && activeLang !== 'original') return

    const errors = activeLang === 'original' ? validateLesson(lesson, t) : null
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
        ?? t('authoring.moduleEditor.saveFailedGeneric')
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
      setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: false } : l)))
    }
  }

  const updateLessonField = (field, value) => {
    if (!selectedLessonId) return
    if (activeLang === 'original') {
      setLessons((ls) =>
        ls.map((l) => (l.id === selectedLessonId ? { ...l, [field]: value, isDirty: true } : l))
      )
    } else {
      setLessons((ls) =>
        ls.map((l) => (l.id === selectedLessonId
          ? {
              ...l,
              translations: { ...l.translations, [activeLang]: { ...(l.translations?.[activeLang] ?? {}), [field]: value } },
              isDirty: true,
            }
          : l))
      )
    }
    // clear validation error for this field on change
    setLessonErrors((prev) => {
      const errs = prev[selectedLessonId]
      if (!errs || !errs[field]) return prev
      const next = { ...errs }
      delete next[field]
      return { ...prev, [selectedLessonId]: next }
    })
  }

  const setLessonGeneralError = (lessonId, message) => {
    setLessonErrors((prev) => {
      const current = prev[lessonId] ?? {}
      if (!message) {
        if (!('general' in current)) return prev
        const { general: _general, ...rest } = current
        return { ...prev, [lessonId]: rest }
      }
      return { ...prev, [lessonId]: { ...current, general: message } }
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
      const detail = err.response?.data?.detail ?? t('authoring.moduleEditor.deleteFailedGeneric')
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

  // ── Translation bar callbacks ─────────────────────────────────────────────

  const reloadTranslations = () => {
    Promise.all([
      client.get(`/authoring/courses/${courseId}/modules/${moduleId}/edit/`),
      client.get(`/authoring/courses/${courseId}/`),
    ]).then(([modRes, courseRes]) => {
      const m = modRes.data
      setModule(m)
      setLessons((ls) => ls.map((l) => {
        const fresh = m.lessons.find((fl) => fl.id === l.id)
        return fresh ? { ...l, translations: fresh.translations } : l
      }))
      setTranslationStatus(courseRes.data.translation_status ?? {})
    }).catch(() => {})
  }

  if (error) return <p className="page-error">{error}</p>
  if (!module) return <p className="page-loading">{t('common.loading')}</p>

  const isAuthor = courseAuthorId != null && user?.id === courseAuthorId
  const isAdmin = user?.profile?.user_type === 'admin'
  const locked = isPublished && !isAuthor && !isAdmin

  return (
    <div className="module-editor-page">

      {/* Top bar */}
      <div className="module-editor-topbar">
        <button className="back-link" onClick={() => navigate(`/authoring/courses/${courseId}`)}>
          <ArrowLeft size={15} /> {t('authoring.moduleEditor.backToCourse')}
        </button>

        <div className="module-editor-topbar-right">
          {saveStatus === 'saved' && <span className="save-msg save-msg--ok">{t('authoring.editor.saved')}</span>}
          {saveStatus === 'error' && <span className="save-msg save-msg--err">{t('authoring.editor.saveFailedShort')}</span>}
          {!locked && moduleDirty && (
            <button
              className="me-save-btn"
              onClick={saveModuleFields}
              disabled={moduleSaving}
            >
              <Save size={15} />
              {moduleSaving ? t('authoring.moduleEditor.saving') : t('authoring.moduleEditor.save')}
            </button>
          )}
          {isPublished && (
            <div className="published-banner">
              <Lock size={14} />
              {locked
                ? t('authoring.editor.publishedBannerLocked')
                : t('authoring.editor.publishedBannerUnlocked')}
            </div>
          )}
        </div>
      </div>

      <h1 className="module-editor-heading">{t('authoring.moduleEditor.moduleEditorHeading')}</h1>

      {/* Language switch + translate */}
      <TranslationBar
        courseId={courseId}
        sourceLanguage={sourceLanguage}
        translationStatus={translationStatus}
        activeLang={activeLang}
        onSelectLang={setActiveLang}
        onStatusUpdate={setTranslationStatus}
        onTranslated={reloadTranslations}
        disabled={locked}
      />

      <div className="module-editor-layout">

        {/* ── Left panel ── */}
        <aside className="module-editor-sidebar">

          <div className="me-card">
            <h2 className="me-card-title">{t('authoring.moduleEditor.moduleStructure')}</h2>
            <label className="me-label">{t('authoring.moduleEditor.moduleTitleLabel')}</label>
            <input
              className="me-input"
              value={moduleFieldValue('title')}
              disabled={locked}
              onChange={(e) => handleModuleFieldChange('title', e.target.value)}
              placeholder={t('authoring.editor.modulePlaceholder')}
            />
            <label className="me-label" style={{ marginTop: '1rem' }}>{t('authoring.moduleEditor.descriptionLabel')}</label>
            <textarea
              className="me-textarea"
              value={moduleFieldValue('description')}
              disabled={locked}
              rows={3}
              onChange={(e) => handleModuleFieldChange('description', e.target.value)}
              placeholder={t('authoring.moduleEditor.moduleOverviewPlaceholder')}
            />
          </div>

          {!locked && !translating && (
            <div className="me-card">
              <h2 className="me-card-title">{t('authoring.moduleEditor.addLessonActivity')}</h2>
              <div className="me-lesson-type-grid">
                {LESSON_TYPES.map(({ type, Icon, color }) => (
                  <button
                    key={type}
                    className={`me-type-btn me-type-btn--${color}`}
                    onClick={() => addLesson(type)}
                  >
                    <Icon size={22} />
                    <span>{t(`lesson.type.${type}`)}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="me-card">
            <h2 className="me-card-title">{t('authoring.moduleEditor.lessonsCount', { count: lessons.length })}</h2>
            <ul className="me-lesson-list">
              {lessons.map((lesson, idx) => {
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
                    draggable={!locked && !translating}
                    onDragStart={(e) => handleDragStart(e, lesson.id)}
                    onDragOver={(e) => handleDragOver(e, lesson.id)}
                    onDrop={(e) => handleDrop(e, lesson.id)}
                    onDragEnd={handleDragEnd}
                  >
                    <GripVertical size={14} className="me-lesson-drag" />
                    <LessonTypeIcon type={lesson.lesson_type} size={15} />
                    <span className="me-lesson-title">{lesson.title || t('authoring.moduleEditor.newLessonTitle', { type: t(`lesson.type.${lesson.lesson_type}`) })}</span>
                    <span className="me-lesson-order">{idx + 1}</span>
                  </li>
                )
              })}
              {lessons.length === 0 && (
                <li className="me-lesson-empty">{t('authoring.moduleEditor.noLessons')}</li>
              )}
            </ul>
          </div>

        </aside>

        {/* ── Right panel ── */}
        <main className="module-editor-main">
          {displayLesson ? (
            <LessonEditor
              lesson={displayLesson}
              locked={locked}
              translating={translating}
              onChange={updateLessonField}
              onDelete={() => deleteLesson(selectedLesson)}
              onSave={() => saveLesson(selectedLesson)}
              onError={(message) => setLessonGeneralError(selectedLesson.id, message)}
              errors={lessonErrors[selectedLesson.id]}
            />
          ) : (
            <div className="me-empty-state">
              <FileText size={40} className="me-empty-icon" />
              <p>{t('authoring.moduleEditor.selectLessonPrompt')}</p>
            </div>
          )}
        </main>

      </div>
    </div>
  )
}
