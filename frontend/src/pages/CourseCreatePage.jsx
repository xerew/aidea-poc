import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Clock, CheckCircle2, Plus, Trash2 } from 'lucide-react'
import client from '../api/client'
// Reuse editor and detail styles — same class names apply
import './CourseDetailPage.css'
import './CourseEditorPage.css'

const PILLAR_COLOR = {
  'teach-with-ai':  'blue',
  'teach-for-ai':   'purple',
  'teach-about-ai': 'green',
}

const EMPTY_FORM = {
  title: '',
  description: '',
  level: 'beginner',
  pillar_id: null,
  duration_hours: 0,
  learning_outcomes: [],
}

export default function CourseCreatePage() {
  const navigate = useNavigate()
  const [pillars, setPillars] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})

  useEffect(() => {
    client.get('/authoring/pillars/').then((res) => {
      setPillars(res.data)
      if (res.data.length) setForm((f) => ({ ...f, pillar_id: res.data[0].id }))
    })
  }, [])

  const currentPillar = pillars.find((p) => p.id === form.pillar_id)
  const pillarColor = PILLAR_COLOR[currentPillar?.slug] ?? 'blue'

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

  const handleCreate = async () => {
    const errs = {}
    if (!form.title.trim()) errs.title = 'Title is required.'
    if (!form.pillar_id) errs.pillar_id = 'Pillar is required.'
    if (Object.keys(errs).length) { setErrors(errs); return }

    setSaving(true)
    setErrors({})
    try {
      const res = await client.post('/authoring/courses/', form)
      navigate(`/authoring/courses/${res.data.id}`)
    } catch {
      setErrors({ submit: 'Failed to create course. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="course-editor">

      {/* Back */}
      <button className="back-link" onClick={() => navigate('/authoring')}>
        <ArrowLeft size={15} /> Back to Authoring
      </button>

      {/* Hero row */}
      <div className="detail-hero">
        <div className="detail-hero-meta">
          <select
            className={`pillar-select pillar-badge pillar-badge--${pillarColor}`}
            value={form.pillar_id ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, pillar_id: Number(e.target.value) }))}
          >
            {pillars.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            className="level-select"
            value={form.level}
            onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div className="editor-save-area">
          {errors.submit && <span className="save-msg save-msg--err">{errors.submit}</span>}
          <button className="enroll-btn" onClick={handleCreate} disabled={saving || !pillars.length}>
            {saving ? 'Creating…' : 'Create Course'}
          </button>
        </div>
      </div>

      {/* Title */}
      <div>
        <input
          className={`editor-title-input${errors.title ? ' input--error' : ''}`}
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          placeholder="Course title"
        />
        {errors.title && <p className="field-error">{errors.title}</p>}
      </div>

      {/* Description */}
      <textarea
        className="editor-desc-input"
        value={form.description}
        onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
        rows={2}
        placeholder="Course description"
      />

      {/* Duration */}
      <div className="detail-stats">
        <span>
          <Clock size={15} />
          <input
            type="number"
            className="editor-inline-number"
            value={form.duration_hours}
            min={0}
            onChange={(e) => setForm((f) => ({ ...f, duration_hours: Number(e.target.value) }))}
          />
          hours
        </span>
      </div>

      {/* Learning Outcomes */}
      <div className="outcomes-card">
        <h2>What You&apos;ll Learn</h2>
        <div className="outcomes-grid">
          {form.learning_outcomes.map((outcome, i) => (
            <div key={i} className="outcome-item outcome-item--edit">
              <CheckCircle2 size={18} className="outcome-icon" />
              <input
                className="editor-outcome-input"
                value={outcome}
                onChange={(e) => updateOutcome(i, e.target.value)}
                placeholder="Learning outcome"
              />
              <button className="icon-btn icon-btn--danger" onClick={() => removeOutcome(i)} title="Remove">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
        <button className="add-dashed-btn" onClick={addOutcome}>
          <Plus size={14} /> Add Outcome
        </button>
      </div>

    </div>
  )
}
