import { useEffect, useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Users, CheckCircle, Target, Award, Download, Search, X } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { downloadXlsx } from '../components/analytics/download'
import './AnalyticsPage.css'

const PER_PAGE = 10

const downloadExport = (ids) => downloadXlsx('/analytics/export/', ids && ids.length ? { ids: ids.join(',') } : {}, 'analytics.xlsx')

const STAT_CARDS = [
  { key: 'total_enrollments', labelKey: 'analytics.stats.totalEnrollments', Icon: Users,       color: 'blue'   },
  { key: 'completion_rate',   labelKey: 'analytics.stats.completionRate',   Icon: CheckCircle, color: 'green'  },
  { key: 'quiz_attempts',     labelKey: 'analytics.stats.quizAttempts',     Icon: Target,      color: 'purple' },
  { key: 'courses_created',   labelKey: 'analytics.stats.coursesCreated',   Icon: Award,       color: 'orange' },
]

StatCard.propTypes = {
  stat: PropTypes.shape({
    key: PropTypes.string,
    labelKey: PropTypes.string,
    Icon: PropTypes.elementType,
    color: PropTypes.string,
  }),
  value: PropTypes.number,
}

function StatCard({ stat, value }) {
  const { t } = useTranslation()
  const { Icon, labelKey, color } = stat
  const display = stat.key === 'completion_rate' ? `${value}%` : value
  return (
    <div className="an-stat-card">
      <div className={`an-stat-icon an-stat-icon--${color}`}>
        <Icon size={22} />
      </div>
      <div>
        <p className="an-stat-value">{display}</p>
        <p className="an-stat-label">{t(labelKey)}</p>
      </div>
    </div>
  )
}

CourseRow.propTypes = {
  course: PropTypes.shape({
    id: PropTypes.number,
    title: PropTypes.string,
    enrolled: PropTypes.number,
    completed: PropTypes.number,
    in_progress: PropTypes.number,
    completion_rate: PropTypes.number,
    avg_time_minutes: PropTypes.number,
    can_view_teachers: PropTypes.bool,
  }),
}

function CourseRow({ course }) {
  const { t } = useTranslation()
  return (
    <div className="an-course-row">
      <div className="an-course-header">
        <span className="an-course-title">{course.title}</span>
        <span className="an-course-pct">{t('analytics.pctCompleted', { pct: course.completion_rate })}</span>
      </div>
      <div className="an-course-stats">
        <div className="an-course-stat an-course-stat--blue">
          <span className="an-course-stat-value">{course.enrolled}</span>
          <span className="an-course-stat-label">{t('analytics.enrolled')}</span>
        </div>
        <div className="an-course-stat an-course-stat--green">
          <span className="an-course-stat-value">{course.completed}</span>
          <span className="an-course-stat-label">{t('analytics.completed')}</span>
        </div>
        <div className="an-course-stat an-course-stat--orange">
          <span className="an-course-stat-value">{course.in_progress}</span>
          <span className="an-course-stat-label">{t('analytics.inProgress')}</span>
        </div>
        <div className="an-course-stat an-course-stat--purple">
          <span className="an-course-stat-value">{t('analytics.avgTimeValue', { minutes: course.avg_time_minutes })}</span>
          <span className="an-course-stat-label">{t('analytics.avgTime')}</span>
        </div>
      </div>
      <div className="an-course-bar-track">
        <div className="an-course-bar-fill" style={{ width: `${course.completion_rate}%` }} />
      </div>

      {course.can_view_teachers && (
        <div className="an-course-actions">
          <Link className="an-course-open" to={`/analytics/courses/${course.id}`}>{t('analytics.open')}</Link>
          <button
            className="an-course-excel"
            onClick={() => downloadXlsx(`/analytics/courses/${course.id}/export/`, {}, `course-${course.id}-analytics.xlsx`).catch(() => {})}
          >
            <Download size={14} /> {t('analytics.excel')}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Export dialog: pick which courses go into the workbook ────────────────────

ExportModal.propTypes = { courses: PropTypes.array.isRequired, onClose: PropTypes.func.isRequired }

function ExportModal({ courses, onClose }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState(() => new Set(courses.map(c => c.id)))
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)

  const allChecked = selected.size === courses.length
  const toggle = (id) => setSelected(prev => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  })
  const toggleAll = () => setSelected(allChecked ? new Set() : new Set(courses.map(c => c.id)))

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return courses
    return courses.filter(c =>
      (c.title || '').toLowerCase().includes(q) || (c.author_name || '').toLowerCase().includes(q))
  }, [courses, query])

  const doExport = async () => {
    setBusy(true)
    try {
      await downloadExport([...selected])
      onClose()
    } catch { setBusy(false) }
  }

  return (
    <div className="an-modal-overlay" onClick={onClose}>
      <div className="an-modal" onClick={(e) => e.stopPropagation()}>
        <div className="an-modal-head">
          <h2>{t('analytics.export.title')}</h2>
          <button className="an-modal-close" onClick={onClose} aria-label={t('common.cancel')}><X size={18} /></button>
        </div>
        <div className="an-search an-modal-search">
          <Search size={15} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('analytics.export.search')} />
        </div>
        <label className="an-modal-all">
          <input type="checkbox" checked={allChecked} onChange={toggleAll} />
          <span>{t('analytics.export.selectAll')}</span>
        </label>
        <div className="an-modal-list">
          {visible.length === 0 ? (
            <p className="an-empty">{t('analytics.noMatch')}</p>
          ) : visible.map(c => (
            <label key={c.id} className="an-modal-item">
              <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} />
              <span className="an-modal-item-title">{c.title}</span>
            </label>
          ))}
        </div>
        <div className="an-modal-actions">
          <button className="an-modal-cancel" onClick={onClose}>{t('common.cancel')}</button>
          <button className="an-export-btn" disabled={busy || selected.size === 0} onClick={doExport}>
            <Download size={15} /> {t('analytics.export.exportSelected', { count: selected.size })}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [pillar, setPillar] = useState('all')
  const [page, setPage] = useState(1)
  const [exportOpen, setExportOpen] = useState(false)

  // Content creators, AIDEA partners and admins all have content-creation access.
  const isCreator = ['content_creator', 'aidea_partner', 'admin'].includes(user?.profile?.user_type)

  useEffect(() => {
    if (!isCreator) return
    client.get('/analytics/overview/')
      .then((res) => setData(res.data))
      .catch(() => setError(t('analytics.loadError')))
  }, [isCreator, t])

  const pillars = useMemo(() => {
    const map = new Map()
    for (const c of data?.courses ?? []) {
      if (c.pillar_slug) map.set(c.pillar_slug, c.pillar_name)
    }
    return [...map.entries()]
  }, [data])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data?.courses ?? []).filter(c =>
      (pillar === 'all' || c.pillar_slug === pillar) &&
      (!q
        || (c.title || '').toLowerCase().includes(q)
        || (c.description || '').toLowerCase().includes(q)
        || (c.author_name || '').toLowerCase().includes(q)),
    )
  }, [data, query, pillar])

  if (!isCreator) {
    return <div className="an-restricted"><p>{t('analytics.restricted')}</p></div>
  }
  if (error) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">{t('common.loading')}</p>

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const pageCourses = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE)
  const onFilter = (setter) => (v) => { setter(v); setPage(1) }

  const handleExport = () => {
    if (data.courses.length > 1) setExportOpen(true)
    else downloadExport(data.courses.map(c => c.id)).catch(() => {})
  }

  return (
    <div className="analytics-page">
      <div className="an-header-row">
        <p className="an-subtitle">{t('analytics.subtitle')}</p>
        <button className="an-export-btn" disabled={data.courses.length === 0} onClick={handleExport}>
          <Download size={15} /> {t('analytics.downloadExcel')}
        </button>
      </div>

      <div className="an-stat-grid">
        {STAT_CARDS.map((stat) => (
          <StatCard key={stat.key} stat={stat} value={data.summary[stat.key]} />
        ))}
      </div>

      <section className="an-section">
        <h2 className="an-section-title">{t('analytics.courseCompletionOverview')}</h2>

        <div className="an-filters">
          <div className="an-search">
            <Search size={15} />
            <input
              value={query}
              onChange={(e) => onFilter(setQuery)(e.target.value)}
              placeholder={t('analytics.searchPlaceholder')}
            />
          </div>
          <select className="an-pillar-select" value={pillar} onChange={(e) => onFilter(setPillar)(e.target.value)}>
            <option value="all">{t('analytics.allPillars')}</option>
            {pillars.map(([slug, name]) => <option key={slug} value={slug}>{name}</option>)}
          </select>
        </div>

        <div className="an-course-list">
          {filtered.length === 0 ? (
            <p className="an-empty">{data.courses.length === 0 ? t('analytics.empty') : t('analytics.noMatch')}</p>
          ) : (
            pageCourses.map((course) => <CourseRow key={course.id} course={course} />)
          )}
        </div>

        {totalPages > 1 && (
          <div className="an-pagination">
            <button disabled={safePage <= 1} onClick={() => setPage(safePage - 1)}>{t('analytics.prev')}</button>
            <span>{t('analytics.pageOf', { page: safePage, total: totalPages })}</span>
            <button disabled={safePage >= totalPages} onClick={() => setPage(safePage + 1)}>{t('analytics.next')}</button>
          </div>
        )}
      </section>

      {exportOpen && <ExportModal courses={data.courses} onClose={() => setExportOpen(false)} />}
    </div>
  )
}
