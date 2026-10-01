import { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { formatDate, formatDuration } from './format'

const STATUSES = ['completed', 'on_track', 'stuck', 'inactive']
const COLUMNS = [
  { key: 'name', label: 'learner' },
  { key: 'progress_pct', label: 'progress' },
  { key: 'active_s', label: 'active' },
  { key: 'visible_s', label: 'onScreen' },
  { key: 'visits', label: 'visits' },
  { key: 'last_active', label: 'lastActive' },
  { key: 'position', label: 'position' },
  { key: 'status', label: 'status' },
]

function compare(key, dir) {
  return (a, b) => {
    const x = key === 'position' ? a.position?.resource ?? '' : a[key]
    const y = key === 'position' ? b.position?.resource ?? '' : b[key]
    if (x == null) return 1
    if (y == null) return -1
    const order = typeof x === 'string' ? x.localeCompare(y) : x - y
    return order * dir
  }
}

LearnersTable.propTypes = {
  learners: PropTypes.arrayOf(PropTypes.object).isRequired,
  onOpen: PropTypes.func.isRequired,
}

export default function LearnersTable({ learners, onOpen }) {
  const { t, i18n } = useTranslation()
  const [sort, setSort] = useState({ key: 'name', dir: 1 })
  const [status, setStatus] = useState('all')
  const counts = useMemo(() => Object.fromEntries(STATUSES.map(s => [s, learners.filter(l => l.status === s).length])), [learners])
  const rows = useMemo(
    () => learners.filter(l => status === 'all' || l.status === status).sort(compare(sort.key, sort.dir)),
    [learners, status, sort],
  )
  const sortBy = (key) => setSort(prev => ({ key, dir: prev.key === key ? -prev.dir : 1 }))

  if (!learners.length) return <p className="acp-empty">{t('analytics.course.empty')}</p>

  return (
    <>
      <select className="acp-status-filter" value={status} onChange={e => setStatus(e.target.value)}>
        <option value="all">{t('analytics.course.status.all')} ({learners.length})</option>
        {STATUSES.map(s => <option key={s} value={s}>{t(`analytics.course.status.${s}`)} ({counts[s]})</option>)}
      </select>
      <div className="acp-table-wrap">
        <table className="acp-table">
          <thead>
            <tr>
              {COLUMNS.map(c => (
                <th key={c.key} className="acp-sortable" onClick={() => sortBy(c.key)}>
                  {t(`analytics.course.col.${c.label}`)}
                  {sort.key === c.key && (sort.dir > 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(l => (
              <tr key={l.user_id} className="acp-row acp-row--learner" onClick={() => onOpen(l.user_id)}>
                <td>
                  <span className="acp-learner-name">{l.name}</span>
                  <span className="acp-learner-email">{l.email}</span>
                </td>
                <td className="acp-num">{l.progress_pct}%</td>
                <td className="acp-num">{l.tracked ? formatDuration(l.active_s, t) : t('analytics.course.notTracked')}</td>
                <td className="acp-num">{l.tracked ? formatDuration(l.visible_s, t) : '—'}</td>
                <td className="acp-num">{l.visits}</td>
                <td>{formatDate(l.last_active, i18n.language)}</td>
                <td className="acp-position">{l.position ? `${l.position.activity} › ${l.position.resource}` : '—'}</td>
                <td><span className={`acp-status acp-status--${l.status}`}>{t(`analytics.course.status.${l.status}`)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
