import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, FileText, Video, Image, HelpCircle, FileDown, ClipboardList, Layers,
  Trash2, GripVertical, Save, Lock, Plus,
} from 'lucide-react'
import client from '../api/client'
import TranslationBar from '../components/authoring/TranslationBar'
import OriginalHint from '../components/authoring/OriginalHint'
import { LANGUAGES } from '../i18n'
import ResourceEditor from '../components/authoring/ResourceEditor'
import { emptyQuestion, mergedQuizData } from '../components/authoring/quizUtils'
import './ModuleEditorPage.css'

// ── Resource type config ──────────────────────────────────────────────────────

const RESOURCE_TYPES = [
  { type: 'text',       Icon: FileText,     color: 'blue'   },
  { type: 'video',      Icon: Video,        color: 'purple' },
  { type: 'image',      Icon: Image,        color: 'green'  },
  { type: 'quiz',       Icon: HelpCircle,   color: 'yellow' },
  { type: 'pdf',        Icon: FileDown,     color: 'red'    },
  { type: 'assignment', Icon: ClipboardList, color: 'indigo' },
]

function typeConfig(type) {
  return RESOURCE_TYPES.find((rt) => rt.type === type) ?? RESOURCE_TYPES[0]
}

// An activity's icon: its resource type when it holds one kind, else "layers".
function ActivityIcon({ activity, size = 16 }) {
  const types = activity.resources?.length
    ? [...new Set(activity.resources.map((r) => r.type))]
    : [activity.lesson_type]
  if (types.length !== 1) return <Layers size={size} className="lesson-type-icon" />
  const { Icon, color } = typeConfig(types[0])
  return <Icon size={size} className={`lesson-type-icon lesson-type-icon--${color}`} />
}

ActivityIcon.propTypes = {
  activity: PropTypes.shape({ resources: PropTypes.array, lesson_type: PropTypes.string }).isRequired,
  size: PropTypes.number,
}

function FieldError({ msg }) {
  if (!msg) return null
  return <p className="lesson-field-error">{msg}</p>
}

FieldError.propTypes = { msg: PropTypes.string }

// ── Translation view of a resource ────────────────────────────────────────────

function displayResource(resource, lang) {
  if (lang === 'original') return resource
  const tr = resource.translations?.[lang] ?? {}
  return {
    ...resource,
    title: tr.title ?? '',
    content: tr.content ?? '',
    caption: tr.caption ?? '',
    instructions: tr.instructions ?? '',
    quiz_data: mergedQuizData(resource, lang),
  }
}

function translationPayload(resource, lang) {
  const tr = resource.translations?.[lang] ?? {}
  const payload = { title: tr.title ?? '' }
  if (resource.type === 'text') payload.content = tr.content ?? ''
  if (['image', 'video', 'pdf'].includes(resource.type)) payload.caption = tr.caption ?? ''
  if (resource.type === 'assignment') payload.instructions = tr.instructions ?? ''
  if (resource.type === 'quiz') payload.quiz_data = mergedQuizData(resource, lang)
  return payload
}

const withFlags = (r) => ({ ...r, isDirty: false, saving: false })

// An unsaved activity: saved (with its first resource) once a resource is picked.
const makeDraft = () => ({
  id: `new-${Date.now()}`,
  title: '',
  description: '',
  lesson_type: 'text',
  duration_minutes: 0,
  resources: [],
  translations: {},
  isDirty: false,
  isNew: true,
  saving: false,
})

// ── Validation ────────────────────────────────────────────────────────────────

function validateActivity(activity, t) {
  if (!activity.title.trim()) return { title: t('authoring.moduleEditor.titleRequiredError') }
  return null
}

function validateResource(resource, t) {
  if (['image', 'video', 'pdf'].includes(resource.type) && !(resource.url || '').trim()) {
    return t('authoring.moduleEditor.mediaUrlRequiredError')
  }
  if (resource.type === 'quiz' && !(resource.quiz_data ?? []).length) {
    return t('authoring.moduleEditor.quizRequiredError')
  }
  if (resource.type === 'assignment' && !(resource.instructions || '').trim()) {
    return t('authoring.moduleEditor.assignmentRequiredError')
  }
  return null
}

// ── Activity editor panel ─────────────────────────────────────────────────────

const activityShape = PropTypes.shape({
  id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  lesson_type: PropTypes.string,
  duration_minutes: PropTypes.number,
  resources: PropTypes.array,
  isDirty: PropTypes.bool,
  isNew: PropTypes.bool,
  saving: PropTypes.bool,
})

function ActivityEditor({
  activity, original, sourceLanguageLabel, resources, locked, translating, errors, resourceErrors,
  onChange, onDelete, onSave,
  onAddResource, onResourceChange, onResourceSave, onResourceDelete, onResourceMove,
}) {
  const { t } = useTranslation()
  const err = errors ?? {}

  // A brand-new, not-yet-saved activity has no `translations` bucket to write
  // into — block translated-mode edits on it until it's saved in the original.
  const blockedNew = activity.isNew && translating
  const fieldsDisabled = locked || blockedNew

  return (
    <div className="lesson-editor-panel">
      <div className="lesson-editor-header">
        <div className="lesson-editor-header-left">
          <div className="lesson-editor-icon-wrap lesson-editor-icon-wrap--blue">
            <ActivityIcon activity={activity} size={20} />
          </div>
          <div>
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
            value={activity.title}
            disabled={fieldsDisabled}
            onChange={(e) => onChange('title', e.target.value)}
            placeholder={t('authoring.moduleEditor.titlePlaceholderExample')}
          />
          {translating && !locked && (
            <OriginalHint text={original.title} onCopy={(v) => onChange('title', v)} language={sourceLanguageLabel} />
          )}
          <FieldError msg={err.title} />
        </div>

        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.descriptionLabel')}</label>
          <textarea
            className="lesson-field-textarea"
            value={activity.description}
            disabled={fieldsDisabled}
            rows={3}
            onChange={(e) => onChange('description', e.target.value)}
            placeholder={t('authoring.moduleEditor.descPlaceholder')}
          />
          {translating && !locked && (
            <OriginalHint text={original.description} onCopy={(v) => onChange('description', v)} language={sourceLanguageLabel} />
          )}
        </div>

        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.durationLabel')}</label>
          <input
            className="lesson-field-input lesson-field-input--short"
            value={activity.duration_minutes || ''}
            disabled={locked || translating}
            type="number"
            min={0}
            onChange={(e) => onChange('duration_minutes', Number(e.target.value))}
            placeholder={t('authoring.moduleEditor.durationPlaceholder')}
          />
        </div>

        <FieldError msg={err.general} />

        {/* A draft is saved by choosing its first resource (below). */}
        {!locked && !activity.isNew && activity.isDirty && (
          <button className="lesson-save-btn" onClick={onSave} disabled={activity.saving}>
            <Save size={15} />
            {activity.saving ? t('authoring.moduleEditor.savingLesson') : t('authoring.moduleEditor.saveLesson')}
          </button>
        )}

        {/* ── Resources ── */}
        <div className="lesson-field">
          <label className="lesson-field-label">{t('authoring.moduleEditor.resource.sectionTitle')}</label>
          <p className="lesson-field-hint">{t('authoring.moduleEditor.resource.sectionHint')}</p>

          {activity.isNew ? (
            !translating && <p className="lesson-field-hint">{t('authoring.moduleEditor.resource.firstResourceHint')}</p>
          ) : (
            <div className="resource-list">
              {resources.map((resource, idx) => (
                <ResourceEditor
                  key={resource.id}
                  resource={resource}
                  original={original.resources?.find((r) => r.id === resource.id)}
                  sourceLanguageLabel={sourceLanguageLabel}
                  index={idx}
                  count={resources.length}
                  locked={locked}
                  translating={translating}
                  error={resourceErrors[resource.id]}
                  onChange={(field, value) => onResourceChange(resource.id, field, value)}
                  onSave={() => onResourceSave(resource.id)}
                  onDelete={() => onResourceDelete(resource.id)}
                  onMove={(dir) => onResourceMove(resource.id, dir)}
                />
              ))}
            </div>
          )}

          {/* Resource picker — always at the bottom of the activity. */}
          {!locked && !translating && (
            <div className="resource-add-panel">
              <span className="resource-add-label">{t('authoring.moduleEditor.resource.addLabel')}</span>
              <div className="resource-add">
                {RESOURCE_TYPES.map(({ type, Icon }) => (
                  <button
                    key={type}
                    type="button"
                    className="resource-add-btn"
                    disabled={activity.saving}
                    onClick={() => onAddResource(type)}
                  >
                    <Icon size={14} /> {t(`lesson.type.${type}`)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

ActivityEditor.propTypes = {
  activity: activityShape.isRequired,
  original: activityShape.isRequired,
  sourceLanguageLabel: PropTypes.string.isRequired,
  resources: PropTypes.array.isRequired,
  locked: PropTypes.bool.isRequired,
  translating: PropTypes.bool.isRequired,
  errors: PropTypes.object,
  resourceErrors: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  onAddResource: PropTypes.func.isRequired,
  onResourceChange: PropTypes.func.isRequired,
  onResourceSave: PropTypes.func.isRequired,
  onResourceDelete: PropTypes.func.isRequired,
  onResourceMove: PropTypes.func.isRequired,
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ModuleEditorPage() {
  const { t } = useTranslation()
  const { id: courseId, moduleId } = useParams()
  const navigate = useNavigate()

  const [module, setModule] = useState(null)
  const [isPublished, setIsPublished] = useState(false)
  const [caps, setCaps] = useState({ canEdit: false, canTranslate: false })
  const [lessons, setLessons] = useState([])
  const [selectedLessonId, setSelectedLessonId] = useState(null)
  const [moduleForm, setModuleForm] = useState({ title: '', description: '' })
  const [moduleDirty, setModuleDirty] = useState(false)
  const [moduleSaving, setModuleSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [error, setError] = useState('')
  const [lessonErrors, setLessonErrors] = useState({})
  const [resourceErrors, setResourceErrors] = useState({})

  // drag-and-drop state
  const [dragId, setDragId] = useState(null)
  const [dragOverId, setDragOverId] = useState(null)

  // ── Translation state ──────────────────────────────────────────────────────
  const [activeLang, setActiveLang] = useState('original')
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [translationStatus, setTranslationStatus] = useState({})
  const translating = activeLang !== 'original'

  const lessonsUrl = `/authoring/courses/${courseId}/modules/${moduleId}/lessons/`
  const resourcesUrl = (activityId) => `${lessonsUrl}${activityId}/resources/`

  useEffect(() => {
    Promise.all([
      client.get(`/authoring/courses/${courseId}/modules/${moduleId}/edit/`),
      client.get(`/authoring/courses/${courseId}/`),
    ])
      .then(([modRes, courseRes]) => {
        const m = modRes.data
        setModule(m)
        setModuleForm({ title: m.title, description: m.description })
        const loaded = m.lessons.map((l) => ({
          ...withFlags(l), isNew: false, resources: (l.resources ?? []).map(withFlags),
        }))
        // The editor always shows an activity: the first one, or a new draft
        // when the module is still empty and the user may edit it.
        if (!loaded.length && courseRes.data.can_edit) {
          const draft = makeDraft()
          setLessons([draft])
          setSelectedLessonId(draft.id)
        } else {
          setLessons(loaded)
          setSelectedLessonId(loaded[0]?.id ?? null)
        }
        setIsPublished(courseRes.data.is_published)
        setCaps({
          canEdit: !!courseRes.data.can_edit,
          canTranslate: !!courseRes.data.can_translate,
        })
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

  // ── Activity helpers ──────────────────────────────────────────────────────

  // Leaving a draft drops it (nothing is saved yet); ask first if the user
  // already typed something. Returns false if they chose to stay.
  const leaveDraft = () => {
    const current = lessons.find((l) => l.id === selectedLessonId)
    if (!current?.isNew) return true
    const typed = (current.title || '').trim() || (current.description || '').trim()
    if (typed && !window.confirm(t('authoring.moduleEditor.discardDraft'))) return false
    setLessons((ls) => ls.filter((l) => l.id !== current.id))
    return true
  }

  const selectLesson = (id) => {
    if (id === selectedLessonId || !leaveDraft()) return
    setSelectedLessonId(id)
  }

  // [+] / "Add activity": a new draft at the bottom of the list. It is saved
  // when the author picks its first resource.
  const addLesson = () => {
    const existing = lessons.find((l) => l.isNew)
    if (existing) { setSelectedLessonId(existing.id); return }
    const draft = makeDraft()
    setLessons((ls) => [...ls, draft])
    setSelectedLessonId(draft.id)
  }

  const saveLessonRequest = async (lesson) => {
    if (activeLang === 'original') {
      const payload = {
        title: lesson.title,
        description: lesson.description,
        duration_minutes: lesson.duration_minutes,
      }
      if (lesson.isNew) {
        payload.lesson_type = lesson.lesson_type
        if (lesson.lesson_type === 'quiz') payload.quiz_data = [emptyQuestion()]
        return (await client.post(lessonsUrl, payload)).data
      }
      return (await client.patch(`${lessonsUrl}${lesson.id}/`, payload)).data
    }
    const payload = {
      title: lesson.translations?.[activeLang]?.title ?? '',
      description: lesson.translations?.[activeLang]?.description ?? '',
    }
    return (await client.patch(`${lessonsUrl}${lesson.id}/?lang=${activeLang}`, payload)).data
  }

  const saveLesson = async (lesson) => {
    if (lesson.isNew && activeLang !== 'original') return

    const errors = activeLang === 'original' ? validateActivity(lesson, t) : null
    if (errors) {
      setLessonErrors((prev) => ({ ...prev, [lesson.id]: errors }))
      return
    }
    setLessonErrors((prev) => { const next = { ...prev }; delete next[lesson.id]; return next })
    setLessons((ls) => ls.map((l) => (l.id === lesson.id ? { ...l, saving: true } : l)))
    try {
      const saved = await saveLessonRequest(lesson)
      setLessons((ls) => ls.map((l) => {
        if (l.id !== lesson.id) return l
        // Keep unsaved resource edits; a new activity takes the server's resources.
        const resources = lesson.isNew ? (saved.resources ?? []).map(withFlags) : l.resources
        return { ...withFlags(saved), isNew: false, resources }
      }))
      setSelectedLessonId(saved.id)
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
    setLessons((ls) => ls.map((l) => {
      if (l.id !== selectedLessonId) return l
      if (activeLang === 'original') return { ...l, [field]: value, isDirty: true }
      return {
        ...l,
        translations: { ...l.translations, [activeLang]: { ...(l.translations?.[activeLang] ?? {}), [field]: value } },
        isDirty: true,
      }
    }))
    setLessonErrors((prev) => {
      const errs = prev[selectedLessonId]
      if (!errs || !errs[field]) return prev
      const next = { ...errs }
      delete next[field]
      return { ...prev, [selectedLessonId]: next }
    })
  }

  // After removing an activity, open the first remaining one (or a new draft).
  const showAfterRemoval = (removedId) => {
    const rest = lessons.filter((l) => l.id !== removedId)
    if (rest.length) {
      setLessons(rest)
      setSelectedLessonId(rest[0].id)
    } else {
      const draft = makeDraft()
      setLessons([draft])
      setSelectedLessonId(draft.id)
    }
  }

  const deleteLesson = async (lesson) => {
    if (lesson.isNew) {
      showAfterRemoval(lesson.id)
      return
    }
    try {
      await client.delete(`${lessonsUrl}${lesson.id}/`)
      showAfterRemoval(lesson.id)
    } catch (err) {
      const detail = err.response?.data?.detail ?? t('authoring.moduleEditor.deleteFailedGeneric')
      setLessonErrors((prev) => ({
        ...prev,
        [lesson.id]: { ...(prev[lesson.id] ?? {}), general: String(detail) },
      }))
    }
  }

  // ── Resource helpers (all act on the selected activity) ──────────────────

  const setResources = (update) => {
    setLessons((ls) => ls.map((l) => (l.id === selectedLessonId ? { ...l, resources: update(l.resources ?? []) } : l)))
  }
  const patchResource = (resourceId, patch) =>
    setResources((rs) => rs.map((r) => (r.id === resourceId ? { ...r, ...patch } : r)))
  const setResourceError = (resourceId, message) => setResourceErrors((prev) => {
    const next = { ...prev }
    if (message) next[resourceId] = message
    else delete next[resourceId]
    return next
  })
  const errorDetail = (err, fallback) => {
    const data = err.response?.data
    const first = data?.detail ?? Object.values(data ?? {})[0]
    return String(Array.isArray(first) ? first[0] : (first ?? fallback))
  }

  const addResource = async (type) => {
    if (selectedLesson?.isNew) {
      // The server creates the activity with a first resource of this type.
      await saveLesson({
        ...selectedLesson,
        lesson_type: type,
        title: (selectedLesson.title || '').trim()
          || t('authoring.moduleEditor.newLessonTitle', { type: t(`lesson.type.${type}`) }),
      })
      return
    }
    try {
      const body = { type, quiz_data: type === 'quiz' ? [emptyQuestion()] : [] }
      const res = await client.post(resourcesUrl(selectedLessonId), body)
      setResources((rs) => [...rs, withFlags(res.data)])
    } catch (err) {
      setLessonErrors((prev) => ({
        ...prev,
        [selectedLessonId]: {
          ...(prev[selectedLessonId] ?? {}),
          general: errorDetail(err, t('authoring.moduleEditor.saveFailedGeneric')),
        },
      }))
    }
  }

  const changeResource = (resourceId, field, value) => {
    setResources((rs) => rs.map((r) => {
      if (r.id !== resourceId) return r
      if (activeLang === 'original') return { ...r, [field]: value, isDirty: true }
      return {
        ...r,
        translations: { ...r.translations, [activeLang]: { ...(r.translations?.[activeLang] ?? {}), [field]: value } },
        isDirty: true,
      }
    }))
    setResourceError(resourceId, '')
  }

  const saveResource = async (resourceId) => {
    const resource = selectedLesson?.resources?.find((r) => r.id === resourceId)
    if (!resource) return
    if (activeLang === 'original') {
      const invalid = validateResource(resource, t)
      if (invalid) { setResourceError(resourceId, invalid); return }
    }
    patchResource(resourceId, { saving: true })
    try {
      const url = `${resourcesUrl(selectedLessonId)}${resourceId}/`
      let res
      if (activeLang === 'original') {
        const { title, content, url: link, caption, quiz_data: quizData, instructions, is_required: isRequired } = resource
        res = await client.patch(url, {
          title, content, url: link, caption, quiz_data: quizData, instructions, is_required: isRequired,
        })
      } else {
        res = await client.patch(`${url}?lang=${activeLang}`, translationPayload(resource, activeLang))
      }
      patchResource(resourceId, withFlags(res.data))
      setResourceError(resourceId, '')
    } catch (err) {
      patchResource(resourceId, { saving: false })
      setResourceError(resourceId, errorDetail(err, t('authoring.moduleEditor.saveFailedGeneric')))
    }
  }

  const deleteResource = async (resourceId) => {
    if (!window.confirm(t('authoring.moduleEditor.resource.confirmDelete'))) return
    try {
      await client.delete(`${resourcesUrl(selectedLessonId)}${resourceId}/`)
      setResources((rs) => rs.filter((r) => r.id !== resourceId))
      setResourceError(resourceId, '')
    } catch (err) {
      setResourceError(resourceId, errorDetail(err, t('authoring.moduleEditor.deleteFailedGeneric')))
    }
  }

  const moveResource = async (resourceId, dir) => {
    const current = selectedLesson?.resources ?? []
    const i = current.findIndex((r) => r.id === resourceId)
    const j = i + dir
    if (i < 0 || j < 0 || j >= current.length) return
    const reordered = [...current]
    ;[reordered[i], reordered[j]] = [reordered[j], reordered[i]]
    setResources(() => reordered)
    try {
      await client.patch(`${resourcesUrl(selectedLessonId)}reorder/`, { order: reordered.map((r) => r.id) })
    } catch { /* silent — visual order already updated */ }
  }

  // ── Drag-and-drop (activities) ────────────────────────────────────────────

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

    // only persist if all activities are saved (no unsaved temp IDs)
    if (!reordered.some((l) => l.isNew)) {
      try {
        await client.patch(`${lessonsUrl}reorder/`, { order: reordered.map((l) => l.id) })
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
        if (!fresh) return l
        return {
          ...l,
          translations: fresh.translations,
          resources: (l.resources ?? []).map((r) => {
            const fr = fresh.resources?.find((x) => x.id === r.id)
            return fr ? { ...r, translations: fr.translations } : r
          }),
        }
      }))
      setTranslationStatus(courseRes.data.translation_status ?? {})
    }).catch(() => {})
  }

  if (error) return <p className="page-error">{error}</p>
  if (!module) return <p className="page-loading">{t('common.loading')}</p>

  // Field lock is mode-aware: source edits need edit rights, translation edits
  // need translate rights (co-editors edit everything; translators only
  // translations).
  const locked = translating ? !caps.canTranslate : !caps.canEdit
  const sourceLangLabel = LANGUAGES.find((l) => l.code === sourceLanguage)?.label ?? sourceLanguage
  const canAddActivity = !locked && !translating

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
        disabled={!caps.canTranslate}
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
            {translating && !locked && (
              <OriginalHint text={moduleForm.title} onCopy={(v) => handleModuleFieldChange('title', v)} language={sourceLangLabel} />
            )}
            <label className="me-label" style={{ marginTop: '1rem' }}>{t('authoring.moduleEditor.descriptionLabel')}</label>
            <textarea
              className="me-textarea"
              value={moduleFieldValue('description')}
              disabled={locked}
              rows={3}
              onChange={(e) => handleModuleFieldChange('description', e.target.value)}
              placeholder={t('authoring.moduleEditor.moduleOverviewPlaceholder')}
            />
            {translating && !locked && (
              <OriginalHint text={moduleForm.description} onCopy={(v) => handleModuleFieldChange('description', v)} language={sourceLangLabel} />
            )}
          </div>

          <div className="me-card">
            <div className="me-card-head">
              <h2 className="me-card-title">
                {t('authoring.moduleEditor.lessonsCount', { count: lessons.filter((l) => !l.isNew).length })}
              </h2>
              {canAddActivity && (
                <button
                  type="button"
                  className="icon-btn me-add-activity-icon"
                  onClick={addLesson}
                  title={t('authoring.moduleEditor.addActivity')}
                  aria-label={t('authoring.moduleEditor.addActivity')}
                >
                  <Plus size={16} />
                </button>
              )}
            </div>
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
                    onClick={() => selectLesson(lesson.id)}
                    draggable={!locked && !translating && !lesson.isNew}
                    onDragStart={(e) => handleDragStart(e, lesson.id)}
                    onDragOver={(e) => handleDragOver(e, lesson.id)}
                    onDrop={(e) => handleDrop(e, lesson.id)}
                    onDragEnd={handleDragEnd}
                  >
                    <GripVertical size={14} className="me-lesson-drag" />
                    <ActivityIcon activity={lesson} size={15} />
                    <span className="me-lesson-title">{lesson.title || t('authoring.moduleEditor.newActivityTitle')}</span>
                    {lesson.isNew
                      ? <span className="me-lesson-draft">{t('authoring.moduleEditor.draftBadge')}</span>
                      : <span className="me-lesson-order">{idx + 1}</span>}
                  </li>
                )
              })}
              {lessons.length === 0 && (
                <li className="me-lesson-empty">{t('authoring.moduleEditor.noLessons')}</li>
              )}
            </ul>
            {canAddActivity && (
              <button type="button" className="add-dashed-btn me-add-activity" onClick={addLesson}>
                <Plus size={14} /> {t('authoring.moduleEditor.addActivity')}
              </button>
            )}
          </div>

        </aside>

        {/* ── Right panel ── */}
        <main className="module-editor-main">
          {displayLesson ? (
            <ActivityEditor
              activity={displayLesson}
              original={selectedLesson}
              sourceLanguageLabel={sourceLangLabel}
              resources={(selectedLesson.resources ?? []).map((r) => displayResource(r, activeLang))}
              locked={locked}
              translating={translating}
              errors={lessonErrors[selectedLesson.id]}
              resourceErrors={resourceErrors}
              onChange={updateLessonField}
              onDelete={() => deleteLesson(selectedLesson)}
              onSave={() => saveLesson(selectedLesson)}
              onAddResource={addResource}
              onResourceChange={changeResource}
              onResourceSave={saveResource}
              onResourceDelete={deleteResource}
              onResourceMove={moveResource}
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
