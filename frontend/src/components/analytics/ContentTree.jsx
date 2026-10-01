import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronRight } from 'lucide-react'
import TypeIcon from '../learner/TypeIcon'
import { formatClock, formatDuration } from './format'

const statsShape = PropTypes.shape({
  reached: PropTypes.number,
  done: PropTypes.number,
  median_active_s: PropTypes.number,
  mean_active_s: PropTypes.number,
  dropped: PropTypes.number,
})

StatCells.propTypes = { stats: statsShape.isRequired, learners: PropTypes.number.isRequired }
function StatCells({ stats, learners }) {
  const { t } = useTranslation()
  const pct = (n) => (learners ? Math.round((n / learners) * 100) : 0)
  let typical = '—'
  if (stats.median_active_s != null) typical = formatDuration(stats.median_active_s, t)
  else if (stats.reached) typical = t('analytics.course.notTracked')
  return (
    <>
      <td className="acp-num">{stats.reached} <span className="acp-pct">({pct(stats.reached)}%)</span></td>
      <td className="acp-num">{stats.done} <span className="acp-pct">({pct(stats.done)}%)</span></td>
      <td
        className="acp-num"
        title={stats.mean_active_s != null ? t('analytics.course.average', { value: formatDuration(stats.mean_active_s, t) }) : undefined}
      >
        {typical}
      </td>
      <td className="acp-num">{stats.dropped || '—'}</td>
    </>
  )
}

ResourceNotes.propTypes = { type: PropTypes.string.isRequired, notes: PropTypes.object.isRequired }
function ResourceNotes({ type, notes }) {
  const { t } = useTranslation()
  const parts = []
  if (type === 'text' && notes.avg_scroll_pct != null) parts.push(t('analytics.course.notes.scroll', { pct: notes.avg_scroll_pct }))
  if (type === 'video') {
    if (notes.avg_watched_pct != null) parts.push(t('analytics.course.notes.watched', { pct: notes.avg_watched_pct }))
    if (notes.typical_stop_s != null) parts.push(t('analytics.course.notes.stop', { time: formatClock(notes.typical_stop_s) }))
  }
  if (type === 'quiz') {
    if (notes.avg_score_pct != null) parts.push(t('analytics.course.notes.score', { pct: notes.avg_score_pct }))
    if (notes.hardest_question) {
      parts.push(t('analytics.course.notes.hardest', { n: notes.hardest_question.number, pct: notes.hardest_question.pct_correct }))
    }
    if (notes.avg_seconds_per_question != null) parts.push(t('analytics.course.notes.perQuestion', { s: notes.avg_seconds_per_question }))
  }
  if ((type === 'pdf' || type === 'image') && notes.opened) parts.push(t('analytics.course.notes.opened', { count: notes.opened }))
  if (type === 'pdf' && notes.downloaded) parts.push(t('analytics.course.notes.downloaded', { count: notes.downloaded }))
  if (type === 'assignment' && notes.submitted) parts.push(t('analytics.course.notes.assignment', notes))
  if (!parts.length) return null
  return <p className="acp-notes" title={notes.hardest_question?.question}>{parts.join(' · ')}</p>
}

Chevron.propTypes = { open: PropTypes.bool.isRequired }
function Chevron({ open }) {
  return open ? <ChevronDown size={14} /> : <ChevronRight size={14} />
}

ContentTree.propTypes = {
  tree: PropTypes.shape({
    learners: PropTypes.number.isRequired,
    modules: PropTypes.arrayOf(PropTypes.object).isRequired,
  }).isRequired,
}

export default function ContentTree({ tree }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(() => new Set(tree.modules.map(m => `m${m.id}`)))
  const toggle = (key) => setOpen((prev) => {
    const next = new Set(prev)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    return next
  })

  if (!tree.modules.length) return <p className="acp-empty">{t('analytics.course.noContent')}</p>

  return (
    <div className="acp-table-wrap">
      <table className="acp-table">
        <thead>
          <tr>
            <th>{t('analytics.course.col.item')}</th>
            <th className="acp-num">{t('analytics.course.col.reached')}</th>
            <th className="acp-num">{t('analytics.course.col.done')}</th>
            <th className="acp-num">{t('analytics.course.col.typical')}</th>
            <th className="acp-num">{t('analytics.course.col.dropped')}</th>
          </tr>
        </thead>
        <tbody>
          {tree.modules.map(m => (
            <ModuleRows key={m.id} module={m} open={open} toggle={toggle} learners={tree.learners} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

ModuleRows.propTypes = {
  module: PropTypes.object.isRequired,
  open: PropTypes.instanceOf(Set).isRequired,
  toggle: PropTypes.func.isRequired,
  learners: PropTypes.number.isRequired,
}
function ModuleRows({ module, open, toggle, learners }) {
  const { t } = useTranslation()
  const mk = `m${module.id}`
  return (
    <>
      <tr className="acp-row acp-row--module" onClick={() => toggle(mk)}>
        <td><Chevron open={open.has(mk)} /> {t('common.moduleLabel', { order: module.order, title: module.title })}</td>
        <StatCells stats={module.stats} learners={learners} />
      </tr>
      {open.has(mk) && module.activities.map(a => {
        const ak = `a${a.id}`
        return [
          <tr key={ak} className="acp-row acp-row--activity" onClick={() => toggle(ak)}>
            <td><Chevron open={open.has(ak)} /> {a.title}</td>
            <StatCells stats={a.stats} learners={learners} />
          </tr>,
          ...(open.has(ak) ? a.resources.map(r => (
            <tr key={`r${r.id}`} className="acp-row acp-row--resource">
              <td>
                <span className="acp-resource-title"><TypeIcon type={r.type} size={14} /> {r.title}</span>
                <ResourceNotes type={r.type} notes={r.notes} />
              </td>
              <StatCells stats={r.stats} learners={learners} />
            </tr>
          )) : []),
        ]
      })}
    </>
  )
}
