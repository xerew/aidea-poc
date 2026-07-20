import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Clock, BookOpen, CheckCircle2, Plus, Trash2, Save, Lock, Pencil, GripVertical } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './CourseEditorPage.css'

const PILLAR_COLOR = {
  'teach-with-ai':  'blue',
  'teach-for-ai':   'purple',
  'teach-about-ai': 'green',
}

export default function CourseEditorPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [pillars, setPillars] = useState([])
  const [form, setForm] = useState(null)
  const [isPublished, setIsPublished] = useState(false)
  const [modules, setModules] = useState([])
  const [author, setAuthor] = useState({ id: null, name: '' })
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [unpublishing, setUnpublishing] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [error, setError] = useState('')
  const [dragModuleId, setDragModuleId] = useState(null)
  const [dragModuleOverId, setDragModuleOverId] = useState(null)

  useEffect(() => {
    Promise.all([
      client.get(`/authoring/courses/${id}/`),
      client.get('/authoring/pillars/'),
    ])
      .then(([courseRes, pillarsRes]) => {
        const c = courseRes.data
        setIsPublished(c.is_published)
        setForm({
          title: c.title,
          description: c.description,
          level: c.level,
          pillar_id: c.pillar.id,
          duration_hours: c.duration_hours,
          learning_outcomes: c.learning_outcomes ?? [],
        })
        setModules(c.modules.map((m) => ({ ...m, isDirty: false, isNew: false, saving: false })))
        setAuthor({ id: c.created_by_id, name: c.created_by_name })
        setPillars(pillarsRes.data)
      })
      .catch(() => setError(t('authoring.editor.loadError')))
  }, [id, t])

  // ── Module API call (used by both per-module save and bulk save) ──────────

  const saveModuleRequest = async (mod) => {
    const payload = { title: mod.title, description: mod.description, duration_minutes: mod.duration_minutes }
    if (mod.isNew) {
      const res = await client.post(`/authoring/courses/${id}/modules/`, payload)
      return { tempId: mod.id, saved: res.data }
    }
    const res = await client.patch(`/authoring/courses/${id}/modules/${mod.id}/`, payload)
    return { tempId: mod.id, saved: res.data }
  }

  // ── Save all (course fields + dirty modules) ─────────────────────────────

  const handleSaveCourse = async () => {
    setSaving(true)
    setSaveStatus('')
    try {
      await client.patch(`/authoring/courses/${id}/`, form)

      const dirtyModules = modules.filter((m) => m.isDirty)
      if (dirtyModules.length) {
        const results = await Promise.allSettled(dirtyModules.map(saveModuleRequest))
        setModules((ms) => {
          const updated = [...ms]
          results.forEach((result) => {
            if (result.status === 'fulfilled') {
              const { tempId, saved } = result.value
              const idx = updated.findIndex((m) => m.id === tempId)
              if (idx !== -1) updated[idx] = { ...saved, isDirty: false, isNew: false, saving: false }
            }
          })
          return updated
        })
      }

      setSaveStatus('saved')
      setTimeout(() => setSaveStatus(''), 3000)
    } catch {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }

  // ── Per-module inline save ────────────────────────────────────────────────

  const saveModule = async (mod) => {
    setModules((ms) => ms.map((m) => (m.id === mod.id ? { ...m, saving: true } : m)))
    try {
      const { saved } = await saveModuleRequest(mod)
      setModules((ms) =>
        ms.map((m) => (m.id === mod.id ? { ...saved, isDirty: false, isNew: false, saving: false } : m))
      )
    } catch {
      setModules((ms) => ms.map((m) => (m.id === mod.id ? { ...m, saving: false } : m)))
    }
  }

  // ── Publish ───────────────────────────────────────────────────────────────

  const handlePublish = async () => {
    if (!window.confirm(t('authoring.editor.confirmPublish'))) return
    setPublishing(true)
    try {
      await client.post(`/authoring/courses/${id}/publish/`)
      setIsPublished(true)
    } catch {
      setSaveStatus('error')
    } finally {
      setPublishing(false)
    }
  }

  // ── Unpublish ────────────────────────────────────────────────────────────

  const handleUnpublish = async () => {
    if (!window.confirm(t('authoring.editor.confirmUnpublish'))) return
    setUnpublishing(true)
    try {
      await client.post(`/authoring/courses/${id}/unpublish/`)
      setIsPublished(false)
    } catch {
      setSaveStatus('error')
    } finally {
      setUnpublishing(false)
    }
  }

  // ── Learning outcomes ────────────────────────────────────────────────────

  const updateOutcome = (i, val) =>
    setForm((f) => {
      const outcomes = [...f.learning_outcomes]
      outcomes[i] = val
      return { ...f, learning_outcomes: outcomes }
    })

  const removeOutcome = (i) =>
    setForm((f) => ({ ...f, learning_outcomes: f.learning_outcomes.filter((_, idx) => idx !== i) }))

  const addOutcome = () =>
    setForm((f) => ({ ...f, learning_outcomes: [...f.learning_outcomes, ''] }))

  // ── Module list helpers ───────────────────────────────────────────────────

  const updateModuleField = (moduleId, field, value) =>
    setModules((ms) =>
      ms.map((m) => (m.id === moduleId ? { ...m, [field]: value, isDirty: true } : m))
    )

  const addModule = () => {
    const tempId = `new-${Date.now()}`
    setModules((ms) => [
      ...ms,
      { id: tempId, title: '', description: '', duration_minutes: 0, order: ms.length + 1, isDirty: true, isNew: true, saving: false },
    ])
  }

  const deleteModule = async (mod) => {
    if (mod.isNew) { setModules((ms) => ms.filter((m) => m.id !== mod.id)); return }
    try {
      await client.delete(`/authoring/courses/${id}/modules/${mod.id}/`)
      setModules((ms) => ms.filter((m) => m.id !== mod.id))
    } catch { /* user can retry */ }
  }

  // ── Module drag-and-drop ─────────────────────────────────────────────────

  const handleModuleDragStart = (e, modId) => {
    setDragModuleId(modId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleModuleDragOver = (e, modId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (modId !== dragModuleOverId) setDragModuleOverId(modId)
  }

  const handleModuleDrop = async (e, targetId) => {
    e.preventDefault()
    setDragModuleOverId(null)
    if (!dragModuleId || dragModuleId === targetId) { setDragModuleId(null); return }

    const fromIdx = modules.findIndex((m) => m.id === dragModuleId)
    const toIdx = modules.findIndex((m) => m.id === targetId)
    const reordered = [...modules]
    reordered.splice(fromIdx, 1)
    reordered.splice(toIdx, 0, modules[fromIdx])
    setModules(reordered)
    setDragModuleId(null)

    const hasNew = reordered.some((m) => m.isNew)
    if (!hasNew) {
      try {
        await client.patch(
          `/authoring/courses/${id}/modules/reorder/`,
          { order: reordered.map((m) => m.id) },
        )
      } catch { /* silent */ }
    }
  }

  const handleModuleDragEnd = () => {
    setDragModuleId(null)
    setDragModuleOverId(null)
  }

  if (error) return <p className="page-error">{error}</p>
  if (!form)  return <p className="page-loading">{t('common.loading')}</p>

  const currentPillar = pillars.find((p) => p.id === form.pillar_id)
  const pillarColor = PILLAR_COLOR[currentPillar?.slug] ?? 'blue'
  const isAuthor = author.id != null && user?.id === author.id
  const isAdmin = user?.profile?.user_type === 'admin'
  const locked = isPublished && !isAuthor && !isAdmin

  return (
    <div className="course-editor">

      {/* Back */}
      <button className="back-link" onClick={() => navigate('/authoring')}>
        <ArrowLeft size={15} /> {t('authoring.editor.backToAuthoring')}
      </button>

      {/* Published banner */}
      {isPublished && (
        <div className="published-banner">
          <Lock size={14} />
          {locked
            ? t('authoring.editor.publishedBannerLocked')
            : t('authoring.editor.publishedBannerUnlocked')}
        </div>
      )}

      {/* Hero row */}
      <div className="detail-hero">
        <div className="detail-hero-meta">
          <select
            className={`pillar-select pillar-badge pillar-badge--${pillarColor}`}
            value={form.pillar_id}
            disabled={locked}
            onChange={(e) => setForm((f) => ({ ...f, pillar_id: Number(e.target.value) }))}
          >
            {pillars.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            className="level-select"
            value={form.level}
            disabled={locked}
            onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}
          >
            <option value="beginner">{t('common.level.beginner')}</option>
            <option value="intermediate">{t('common.level.intermediate')}</option>
            <option value="advanced">{t('common.level.advanced')}</option>
          </select>
        </div>

        {!locked && (
          <div className="editor-save-area">
            {saveStatus === 'saved' && <span className="save-msg save-msg--ok">{t('authoring.editor.saved')}</span>}
            {saveStatus === 'error' && <span className="save-msg save-msg--err">{t('authoring.editor.saveFailedShort')}</span>}
            <button className="enroll-btn enroll-btn--outline" onClick={handleSaveCourse} disabled={saving}>
              {saving ? t('common.saving') : t('authoring.editor.saveChanges')}
            </button>
            {!isPublished && (
              <button className="enroll-btn" onClick={handlePublish} disabled={publishing}>
                {publishing ? t('authoring.editor.publishing') : t('authoring.editor.publish')}
              </button>
            )}
            {isPublished && (isAuthor || isAdmin) && (
              <button className="enroll-btn enroll-btn--outline" onClick={handleUnpublish} disabled={unpublishing}>
                {unpublishing ? t('authoring.editor.unpublishing') : t('authoring.editor.unpublish')}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Title */}
      <input
        className="editor-title-input"
        value={form.title}
        disabled={locked}
        onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
        placeholder={t('authoring.editor.courseTitlePlaceholder')}
      />

      {/* Author */}
      {author.name && <p className="course-editor-author">{t('authoring.editor.authorLabel', { name: author.name })}</p>}

      {/* Description */}
      <textarea
        className="editor-desc-input"
        value={form.description}
        disabled={locked}
        onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
        rows={2}
        placeholder={t('authoring.editor.courseDescPlaceholder')}
      />

      {/* Stats */}
      <div className="detail-stats">
        <span>
          <Clock size={15} />
          <input
            type="number"
            className="editor-inline-number"
            value={form.duration_hours}
            min={0}
            disabled={locked}
            onChange={(e) => setForm((f) => ({ ...f, duration_hours: Number(e.target.value) }))}
          />
          {t('authoring.editor.hours')}
        </span>
        <span><BookOpen size={15} /> {t('common.moduleCount', { count: modules.length })}</span>
      </div>

      {/* Learning Outcomes */}
      <div className="outcomes-card">
        <h2>{t('courseDetail.whatYoullLearn')}</h2>
        <div className="outcomes-grid">
          {form.learning_outcomes.map((outcome, i) => (
            <div key={i} className="outcome-item outcome-item--edit">
              <CheckCircle2 size={18} className="outcome-icon" />
              <input
                className="editor-outcome-input"
                value={outcome}
                disabled={locked}
                onChange={(e) => updateOutcome(i, e.target.value)}
                placeholder={t('authoring.editor.outcomePlaceholder')}
              />
              {!locked && (
                <button className="icon-btn icon-btn--danger" onClick={() => removeOutcome(i)} title={t('authoring.editor.removeOutcome')}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
        {!locked && (
          <button className="add-dashed-btn" onClick={addOutcome}>
            <Plus size={14} /> {t('authoring.editor.addOutcome')}
          </button>
        )}
      </div>

      {/* Modules */}
      <section className="modules-section">
        <h2>{t('courseDetail.courseModules')}</h2>
        <div className="modules-list">
          {modules.map((mod, idx) => {
            const isModDragOver = dragModuleOverId === mod.id && dragModuleId !== mod.id
            return (
            <div
              key={mod.id}
              className={[
                'module-row module-row--edit',
                dragModuleId === mod.id ? 'module-row--dragging' : '',
                isModDragOver ? 'module-row--drag-over' : '',
              ].filter(Boolean).join(' ')}
              draggable={!locked}
              onDragStart={(e) => handleModuleDragStart(e, mod.id)}
              onDragOver={(e) => handleModuleDragOver(e, mod.id)}
              onDrop={(e) => handleModuleDrop(e, mod.id)}
              onDragEnd={handleModuleDragEnd}
            >
              <div className="module-number">
                {!locked && <GripVertical size={14} className="module-drag-handle" />}
                {idx + 1}
              </div>
              <div className="module-body">
                <input
                  className="editor-module-title"
                  value={mod.title}
                  disabled={locked}
                  onChange={(e) => updateModuleField(mod.id, 'title', e.target.value)}
                  placeholder={t('authoring.editor.modulePlaceholder')}
                />
                <textarea
                  className="editor-module-desc"
                  value={mod.description}
                  disabled={locked}
                  onChange={(e) => updateModuleField(mod.id, 'description', e.target.value)}
                  rows={1}
                  placeholder={t('authoring.editor.moduleDescPlaceholder')}
                />
                <div className="module-meta editor-module-meta">
                  <input
                    type="number"
                    className="editor-inline-number"
                    value={mod.duration_minutes}
                    min={0}
                    disabled={locked}
                    onChange={(e) => updateModuleField(mod.id, 'duration_minutes', Number(e.target.value))}
                  />
                  <span>{t('authoring.editor.min')}</span>
                </div>
              </div>
              <div className="module-editor-actions">
                {!mod.isNew && (
                  <button
                    className="icon-btn"
                    onClick={() => navigate(`/authoring/courses/${id}/modules/${mod.id}`)}
                    title={t('authoring.editor.editModuleLessons')}
                  >
                    <Pencil size={15} />
                  </button>
                )}
                {!locked && mod.isDirty && (
                  <button
                    className="icon-btn icon-btn--save"
                    onClick={() => saveModule(mod)}
                    disabled={mod.saving}
                    title={t('authoring.editor.saveModule')}
                  >
                    <Save size={15} />
                  </button>
                )}
                {!locked && (
                  <button
                    className="icon-btn icon-btn--danger"
                    onClick={() => deleteModule(mod)}
                    title={t('authoring.editor.deleteModule')}
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </div>
          )})}
        </div>
        {!locked && (
          <button className="add-dashed-btn" onClick={addModule}>
            <Plus size={15} /> {t('authoring.editor.addModule')}
          </button>
        )}
      </section>

    </div>
  )
}
