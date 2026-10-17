import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp, Check, Plus, Sparkles, Trash2 } from 'lucide-react'
import client from '../../api/client'
import { kappaText, percent } from '../reviews/aiReview'
import './AIReviewPanel.css'

const MAX_EXAMPLES = 5

// A new criterion gets the next free id (c1, c2, …) so ids never collide.
const nextId = (criteria) => {
  const used = criteria.map(c => Number(/^c(\d+)$/.exec(c.id ?? '')?.[1] ?? 0))
  return `c${Math.max(0, ...used) + 1}`
}

function CriteriaEditor({ criteria, locked, onChange }) {
  const { t } = useTranslation()
  const update = (i, field, value) => onChange(criteria.map((c, j) => (j === i ? { ...c, [field]: value } : c)))
  const move = (i, dir) => {
    const next = [...criteria]
    const [item] = next.splice(i, 1)
    next.splice(i + dir, 0, item)
    onChange(next)
  }
  return (
    <div className="air-criteria-editor">
      {criteria.map((c, i) => (
        <div key={c.id} className="air-crit-row">
          <input type="text" className="air-crit-name" value={c.name} disabled={locked}
            placeholder={t('authoring.aiReview.criterionName')} onChange={(e) => update(i, 'name', e.target.value)} />
          <input type="text" className="air-crit-met" value={c.met} disabled={locked}
            placeholder={t('authoring.aiReview.criterionMet')} onChange={(e) => update(i, 'met', e.target.value)} />
          <label className="air-crit-required">
            <input type="checkbox" checked={c.required} disabled={locked}
              onChange={(e) => update(i, 'required', e.target.checked)} />
            {t('authoring.aiReview.required')}
          </label>
          {!locked && (
            <span className="air-crit-tools">
              <button type="button" className="me-media-btn" disabled={i === 0} onClick={() => move(i, -1)}
                title={t('authoring.aiReview.moveUp')}><ArrowUp size={14} /></button>
              <button type="button" className="me-media-btn" disabled={i === criteria.length - 1} onClick={() => move(i, 1)}
                title={t('authoring.aiReview.moveDown')}><ArrowDown size={14} /></button>
              <button type="button" className="me-media-btn me-media-btn--danger"
                onClick={() => onChange(criteria.filter((_, j) => j !== i))}
                title={t('authoring.aiReview.remove')}><Trash2 size={14} /></button>
            </span>
          )}
        </div>
      ))}
      {!locked && (
        <button type="button" className="lesson-upload-btn air-add"
          onClick={() => onChange([...criteria, { id: nextId(criteria), name: '', met: '', required: true }])}>
          <Plus size={14} /> {t('authoring.aiReview.addCriterion')}
        </button>
      )}
    </div>
  )
}

CriteriaEditor.propTypes = {
  criteria: PropTypes.array.isRequired,
  locked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
}

function ExamplesList({ examples, locked, onAdd, onRemove }) {
  const { t } = useTranslation()
  const [form, setForm] = useState({ text: '', verdict: 'approve', reason: '' })
  const full = examples.length >= MAX_EXAMPLES
  const verdictLabel = (v) => t(v === 'approve' ? 'authoring.aiReview.verdictApprove' : 'authoring.aiReview.verdictChanges')
  return (
    <div className="air-examples">
      {examples.map(ex => (
        <div key={ex.id} className="air-example">
          <div className="air-example-text">
            <strong>{verdictLabel(ex.verdict)}</strong>{ex.reason ? ` — ${ex.reason}` : ''}
            <p>{ex.text}</p>
          </div>
          {!locked && (
            <button type="button" className="me-media-btn me-media-btn--danger" onClick={() => onRemove(ex.id)}
              title={t('authoring.aiReview.remove')}><Trash2 size={14} /></button>
          )}
        </div>
      ))}
      {!locked && (full ? <p className="air-hint">{t('authoring.aiReview.maxExamples')}</p> : (
        <div className="air-example-form">
          <textarea value={form.text} placeholder={t('authoring.aiReview.exampleText')}
            onChange={(e) => setForm({ ...form, text: e.target.value })} />
          <div className="air-example-form-row">
            <select value={form.verdict} aria-label={t('authoring.aiReview.verdict')}
              onChange={(e) => setForm({ ...form, verdict: e.target.value })}>
              <option value="approve">{verdictLabel('approve')}</option>
              <option value="changes_requested">{verdictLabel('changes_requested')}</option>
            </select>
            <input type="text" value={form.reason} placeholder={t('authoring.aiReview.reason')}
              onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            <button type="button" className="lesson-upload-btn" disabled={!form.text.trim()}
              onClick={async () => { if (await onAdd(form)) setForm({ text: '', verdict: 'approve', reason: '' }) }}>
              <Plus size={14} /> {t('authoring.aiReview.addExample')}
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

ExamplesList.propTypes = {
  examples: PropTypes.array.isRequired,
  locked: PropTypes.bool.isRequired,
  onAdd: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
}

/** Assignment resource: AI reviewer set-up — rubric, examples, checks, visibility, auto-approve. */
export default function AIReviewPanel({ aiReviewUrl, locked }) {
  const { t } = useTranslation()
  const [config, setConfig] = useState(null)
  const [criteria, setCriteria] = useState([])
  const [examples, setExamples] = useState([])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all([client.get(aiReviewUrl), client.get(`${aiReviewUrl}examples/`)])
      .then(([cfg, ex]) => {
        if (!alive) return
        setConfig(cfg.data)
        setCriteria(cfg.data.criteria)
        setExamples(ex.data)
      })
      .catch(() => { if (alive) setError(t('authoring.aiReview.errors.generic')) })
    return () => { alive = false }
  }, [aiReviewUrl, t])

  const fail = (err) => setError(err.response?.status === 503
    ? t('authoring.aiReview.errors.offline')
    : (err.response?.data?.detail ?? t('authoring.aiReview.errors.generic')))

  const save = async (patch) => {
    setBusy('save')
    setError('')
    try {
      const res = await client.put(aiReviewUrl, patch)
      setConfig(res.data)
      if ('criteria' in patch) setCriteria(res.data.criteria)
    } catch (err) {
      fail(err)
    } finally {
      setBusy('')
    }
  }

  const draft = async () => {
    setBusy('draft')
    setError('')
    try {
      const res = await client.post(`${aiReviewUrl}draft/`)
      setCriteria(res.data.criteria)
    } catch (err) {
      fail(err)
    } finally {
      setBusy('')
    }
  }

  const addExample = async (form) => {
    setError('')
    try {
      const res = await client.post(`${aiReviewUrl}examples/`, form)
      setExamples(prev => [...prev, res.data])
      return true
    } catch (err) {
      fail(err)
      return false
    }
  }

  const removeExample = async (id) => {
    setError('')
    try {
      await client.delete(`${aiReviewUrl}examples/${id}/`)
      setExamples(prev => prev.filter(e => e.id !== id))
    } catch (err) {
      fail(err)
    }
  }

  if (!config) return error ? <p className="media-item-error">{error}</p> : null
  const dirty = JSON.stringify(criteria) !== JSON.stringify(config.criteria)
  const { stats } = config
  const disabled = locked || Boolean(busy)

  return (
    <div className="air-panel">
      <div className="air-head">
        <span className="air-title"><Sparkles size={15} /> {t('authoring.aiReview.title')}</span>
        <label className="resource-editor-required">
          <input type="checkbox" checked={config.enabled} disabled={disabled}
            onChange={(e) => save({ enabled: e.target.checked })} />
          {t('authoring.aiReview.enable')}
        </label>
      </div>
      {!config.platform_enabled && <p className="air-hint">{t('authoring.aiReview.platformOff')}</p>}

      {config.enabled && (
        <>
          <div className="air-section">
            <div className="air-section-head">
              <p className="lesson-field-label">{t('authoring.aiReview.rubric')}</p>
              {config.rubric_approved && !dirty
                ? <span className="air-badge air-badge--ok"><Check size={13} /> {t('authoring.aiReview.approved')}</span>
                : <span className="air-badge air-badge--warn">{t('authoring.aiReview.unapproved')}</span>}
            </div>
            <CriteriaEditor criteria={criteria} locked={disabled} onChange={setCriteria} />
            {!locked && (
              <div className="air-actions">
                <button type="button" className="lesson-upload-btn" disabled={disabled} onClick={draft}>
                  <Sparkles size={14} /> {busy === 'draft' ? t('authoring.aiReview.drafting') : t('authoring.aiReview.draft')}
                </button>
                <button type="button" className="lesson-upload-btn air-approve"
                  disabled={disabled || criteria.length === 0 || criteria.some(c => !c.name.trim()) || (config.rubric_approved && !dirty)}
                  onClick={() => save({ criteria, rubric_approved: true })}>
                  <Check size={14} /> {t('authoring.aiReview.approve')}
                </button>
              </div>
            )}
          </div>

          <div className="air-section">
            <p className="lesson-field-label">{t('authoring.aiReview.examples')}</p>
            <ExamplesList examples={examples} locked={locked} onAdd={addExample} onRemove={removeExample} />
          </div>

          <div className="air-section">
            <label className="resource-editor-required">
              <input type="checkbox" checked={config.duplicate_check} disabled={disabled}
                onChange={(e) => save({ duplicate_check: e.target.checked })} />
              {t('authoring.aiReview.duplicateCheck')}
            </label>
            <label className="resource-editor-required air-soon">
              <input type="checkbox" checked={false} disabled readOnly />
              {t('authoring.aiReview.trustAiSoon')}
            </label>
            <label className="resource-editor-required">
              <input type="checkbox" checked={config.learner_visible} disabled={disabled}
                onChange={(e) => save({ learner_visible: e.target.checked })} />
              {t('authoring.aiReview.learnerVisible')}
            </label>
            <label className="resource-editor-required">
              <input type="checkbox" checked={config.auto_approve} disabled={disabled || (!config.unlocked && !config.auto_approve)}
                onChange={(e) => save({ auto_approve: e.target.checked })} />
              {t('authoring.aiReview.autoApprove')}
            </label>
            {!config.unlocked && (
              <p className="air-hint">{t('authoring.aiReview.autoLocked', {
                min: config.unlock_min_reviews, pct: percent(config.unlock_min_lower_bound),
                decided: stats.decided, now: percent(stats.approve_lower_bound),
              })}</p>
            )}
          </div>

          {stats.reviews > 0 && (
            <p className="air-stats">{t('authoring.aiReview.stats', {
              reviews: stats.reviews, agreement: percent(stats.agreement), kappa: kappaText(stats.kappa),
              approvals: percent(stats.approve_agreement), unchanged: percent(stats.feedback_unchanged),
              missed: stats.most_missed_name ?? '—',
            })}</p>
          )}
        </>
      )}
      {error && <p className="media-item-error">{error}</p>}
    </div>
  )
}

AIReviewPanel.propTypes = {
  aiReviewUrl: PropTypes.string.isRequired,
  locked: PropTypes.bool.isRequired,
}
