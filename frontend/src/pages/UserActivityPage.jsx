import { useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Download, ExternalLink } from 'lucide-react'
import client from '../api/client'
import { downloadXlsx } from '../components/analytics/download'
import { createLatest } from '../lib/latestRequest'
import { matomoVisitorLogUrl } from '../lib/matomoLink'
import './UserActivityPage.css'

// Admin-only: everything one person does on the platform (spec 2026-11-21).
const FILTERS = ['all', 'learning', 'authoring', 'reviews', 'account']
const ROLE_KEYS = { teacher: 'teacher', content_creator: 'contentCreator', aidea_partner: 'aideaPartner', admin: 'admin' }

function levelForScore(score) {
  if (score <= 2) return 'beginner'
  if (score <= 4) return 'intermediate'
  return 'advanced'
}

function languageName(code, uiLanguage) {
  try {
    return new Intl.DisplayNames([uiLanguage], { type: 'language' }).of(code) || code
  } catch {
    return code
  }
}

// One feed line in the viewer's language; the English `text` from the server
// is the fallback for a kind this build doesn't know yet.
function feedText(item, t, i18n) {
  const roleLabel = (role) => (ROLE_KEYS[role] ? t(`admin.roles.${ROLE_KEYS[role]}`) : role)
  const p = { ...item.params, course: item.course?.title ?? item.params.course ?? '' }
  if (p.outcome) p.outcome = t(`admin.activity.outcomes.${p.outcome}`)
  if (item.kind === 'collaborator_added' && p.role) p.role = t(`admin.activity.authorRoles.${p.role}`)
  if (p.old_role) p.old_role = roleLabel(p.old_role)
  if (p.new_role) p.new_role = roleLabel(p.new_role)
  if (p.language) p.language = languageName(p.language, i18n.language)
  if (item.kind === 'signed_in') {
    p.device = t(`admin.activity.devices.${p.device || 'unknown'}`)
    p.browser = p.browser || 'Other'
  }
  const key = `admin.activity.kinds.${item.kind}`
  let text = i18n.exists(key) ? t(key, p) : item.text
  if (item.kind === 'h5p_attempt' && p.score != null && p.max_score != null) text += ` (${p.score}/${p.max_score})`
  return text
}

Section.propTypes = { title: PropTypes.string.isRequired, children: PropTypes.node }

function Section({ title, children }) {
  return (
    <section className="ua-section">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

export default function UserActivityPage() {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [category, setCategory] = useState('all')
  const [items, setItems] = useState([])
  const [nextBefore, setNextBefore] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  // Filter switches and "Load more" can overlap; only the newest response is used.
  const latest = useRef(createLatest())

  useEffect(() => {
    client.get(`/admin/users/${id}/activity/`)
      .then(({ data: d }) => { setData(d); setItems(d.feed); setNextBefore(d.next_before) })
      .catch(() => setError(t('admin.activity.loadError')))
  }, [id, t])

  const fetchFeed = async (cat, before) => {
    const params = {}
    if (cat !== 'all') params.category = cat
    if (before) params.before = before
    const { data: page } = await client.get(`/admin/users/${id}/activity/feed/`, { params })
    return page
  }

  const changeFilter = async (cat) => {
    const request = latest.current.start()
    setCategory(cat)
    setLoadingMore(false)
    try {
      const page = await fetchFeed(cat, null)
      if (!latest.current.isCurrent(request)) return
      setItems(page.items)
      setNextBefore(page.next_before)
      setError('')
    } catch {
      if (latest.current.isCurrent(request)) setError(t('admin.activity.loadError'))
    }
  }

  const loadMore = async () => {
    const request = latest.current.start()
    setLoadingMore(true)
    try {
      const page = await fetchFeed(category, nextBefore)
      if (!latest.current.isCurrent(request)) return
      setItems((prev) => [...prev, ...page.items])
      setNextBefore(page.next_before)
      setError('')
    } catch {
      if (latest.current.isCurrent(request)) setError(t('admin.activity.loadError'))
    } finally {
      if (latest.current.isCurrent(request)) setLoadingMore(false)
    }
  }

  if (error && !data) return <p className="page-error">{error}</p>
  if (!data) return <p className="page-loading">{t('common.loading')}</p>

  const { summary: s, courses, authoring, logins } = data
  const when = (iso) => (iso ? new Date(iso).toLocaleString(i18n.language) : t('admin.activity.never'))
  const day = (iso) => (iso ? new Date(iso).toLocaleDateString(i18n.language) : '—')
  const minutes = (seconds) => t('admin.activity.minutes', { count: Math.round((seconds || 0) / 60) })
  const roleLabel = ROLE_KEYS[s.role] ? t(`admin.roles.${ROLE_KEYS[s.role]}`) : (s.role || '—')
  const matomoUrl = matomoVisitorLogUrl(import.meta.env, s.id)
  const download = async () => {
    setDownloading(true)
    setDownloadError('')
    try {
      await downloadXlsx(`/admin/users/${id}/activity/export/`, {}, `${s.username}-activity.xlsx`)
    } catch {
      setDownloadError(t('admin.activity.downloadError'))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="ua-page">
      <Link to="/admin/users" className="ua-back"><ArrowLeft size={16} /> {t('admin.activity.back')}</Link>

      <header className="ua-header">
        <div>
          <h1>{s.name}</h1>
          <p className="ua-sub">@{s.username} · {s.email || '—'} · {roleLabel}</p>
        </div>
        <div className="ua-actions">
          <button type="button" className="ua-btn ua-btn--primary" onClick={download} disabled={downloading}>
            <Download size={16} /> {downloading ? t('common.loading') : t('admin.activity.download')}
          </button>
          {matomoUrl && (
            <a className="ua-btn" href={matomoUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink size={16} /> {t('admin.activity.openMatomo')}
            </a>
          )}
        </div>
        {downloadError && <p className="ua-download-error" role="alert">{downloadError}</p>}
      </header>

      <Section title={t('admin.activity.summary')}>
        <dl className="ua-summary">
          <div><dt>{t('admin.activity.fields.role')}</dt><dd>{roleLabel}</dd></div>
          <div><dt>{t('admin.activity.fields.joined')}</dt><dd>{day(s.joined)}</dd></div>
          <div><dt>{t('admin.activity.fields.lastLogin')}</dt><dd>{when(s.last_login)}</dd></div>
          <div><dt>{t('admin.activity.fields.onboarding')}</dt><dd>{s.onboarding_completed ? t('admin.activity.yes') : t('admin.activity.no')}</dd></div>
          <div>
            <dt>{t('admin.activity.fields.competency')}</dt>
            <dd>{s.competency_score == null ? '—' : `${t(`common.level.${levelForScore(s.competency_score)}`)} (${s.competency_score})`}</dd>
          </div>
          <div><dt>{t('admin.activity.fields.totalTime')}</dt><dd>{minutes(s.total_active_s)}</dd></div>
          <div><dt>{t('admin.activity.fields.logins30d')}</dt><dd>{s.logins_30d}</dd></div>
        </dl>
      </Section>

      <Section title={t('admin.activity.courses')}>
        {courses.length === 0 ? <p className="ua-empty">{t('admin.activity.empty')}</p> : (
          <div className="ua-table-wrap">
            <table className="ua-table">
              <thead>
                <tr>
                  <th>{t('admin.activity.cols.course')}</th><th>{t('admin.activity.cols.pillar')}</th>
                  <th>{t('admin.activity.cols.progress')}</th><th>{t('admin.activity.cols.time')}</th>
                  <th>{t('admin.activity.cols.status')}</th><th>{t('admin.activity.cols.enrolled')}</th>
                  <th>{t('admin.activity.cols.lastActive')}</th>
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr key={c.course_id}>
                    <td><Link to={`/analytics/courses/${c.course_id}?learner=${s.id}`}>{c.title}</Link></td>
                    <td>{c.pillar}</td>
                    <td>{c.progress_pct}%</td>
                    <td>{minutes(c.active_s)}</td>
                    <td>{t(`analytics.course.status.${c.status}`)}</td>
                    <td>{day(c.enrolled_at)}</td>
                    <td>{when(c.last_active)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {authoring.length > 0 && (
        <Section title={t('admin.activity.authoring')}>
          <div className="ua-table-wrap">
            <table className="ua-table">
              <thead>
                <tr>
                  <th>{t('admin.activity.cols.course')}</th><th>{t('admin.activity.cols.role')}</th>
                  <th>{t('admin.activity.cols.published')}</th><th>{t('admin.activity.cols.edits')}</th>
                </tr>
              </thead>
              <tbody>
                {authoring.map((a) => (
                  <tr key={`${a.course_id}-${a.role}`}>
                    <td>{a.title}</td>
                    <td>{t(`admin.activity.authorRoles.${a.role}`)}</td>
                    <td>{a.is_published ? t('admin.activity.yes') : t('admin.activity.no')}</td>
                    <td>{a.edits}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      <Section title={t('admin.activity.feed')}>
        <div className="ua-filters" role="group" aria-label={t('admin.activity.feed')}>
          {FILTERS.map((f) => (
            <button key={f} type="button" className={`ua-chip${category === f ? ' ua-chip--on' : ''}`}
              aria-pressed={category === f} onClick={() => changeFilter(f)}>
              {t(`admin.activity.filters.${f}`)}
            </button>
          ))}
        </div>
        {items.length === 0 ? <p className="ua-empty">{t('admin.activity.empty')}</p> : (
          <ul className="ua-feed">
            {items.map((item, i) => (
              <li key={`${item.at}-${item.kind}-${i}`} className={`ua-feed-item ua-feed-item--${item.category}`}>
                <time className="ua-feed-time">{when(item.at)}</time>
                <span>{feedText(item, t, i18n)}</span>
              </li>
            ))}
          </ul>
        )}
        {nextBefore && (
          <button type="button" className="ua-btn" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? t('common.loading') : t('admin.activity.loadMore')}
          </button>
        )}
        {error && <p className="page-error">{error}</p>}
      </Section>

      <Section title={t('admin.activity.logins')}>
        {logins.length === 0 ? <p className="ua-empty">{t('admin.activity.noLogins')}</p> : (
          <div className="ua-table-wrap">
            <table className="ua-table">
              <thead>
                <tr>
                  <th>{t('admin.activity.cols.when')}</th><th>{t('admin.activity.cols.device')}</th>
                  <th>{t('admin.activity.cols.browser')}</th>
                </tr>
              </thead>
              <tbody>
                {logins.map((l, i) => (
                  <tr key={`${l.at}-${i}`}>
                    <td>{when(l.at)}</td>
                    <td>{t(`admin.activity.devices.${l.device || 'unknown'}`)}</td>
                    <td>{l.browser || 'Other'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  )
}
