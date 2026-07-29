import { useCallback, useEffect, useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Search } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './AdminPage.css'

const PER_PAGE = 10

// A person matches the query if it appears in their name, username or email.
function personMatches(p, query) {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    `${p.first_name ?? ''} ${p.last_name ?? ''}`.toLowerCase().includes(q) ||
    (p.username ?? '').toLowerCase().includes(q) ||
    (p.email ?? '').toLowerCase().includes(q)
  )
}

AdminSearch.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
}

function AdminSearch({ value, onChange, placeholder }) {
  return (
    <div className="admin-search">
      <Search size={15} className="admin-search-icon" />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  )
}

Pagination.propTypes = {
  page: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  onPage: PropTypes.func.isRequired,
}

function Pagination({ page, totalPages, onPage }) {
  const { t } = useTranslation()
  if (totalPages <= 1) return null
  return (
    <div className="admin-pagination">
      <button className="admin-page-btn" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {t('admin.prev')}
      </button>
      <span className="admin-page-info">{t('admin.pageOf', { page, total: totalPages })}</span>
      <button className="admin-page-btn" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
        {t('admin.next')}
      </button>
    </div>
  )
}


// ── Users tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { t } = useTranslation()
  const { user: me } = useAuth()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [feedback, setFeedback] = useState({})
  const [query,    setQuery]    = useState('')
  const [page,     setPage]     = useState(1)

  const filtered = useMemo(() => users.filter((u) => personMatches(u, query)), [users, query])
  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const pageUsers = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE)

  const onSearch = (value) => { setQuery(value); setPage(1) }

  const ROLE_LABELS = {
    teacher: t('admin.roles.teacher'),
    content_creator: t('admin.roles.contentCreator'),
    aidea_partner: t('admin.roles.aideaPartner'),
    admin: t('admin.roles.admin'),
  }

  useEffect(() => {
    client.get('/admin/users/')
      .then(({ data }) => {
        const ROLE_ORDER = { admin: 0, content_creator: 1, aidea_partner: 2, teacher: 3 }
        const sorted = [...data].sort((a, b) => {
          const ro = (ROLE_ORDER[a.user_type] ?? 9) - (ROLE_ORDER[b.user_type] ?? 9)
          if (ro !== 0) return ro
          const name = (a.last_name || a.username).localeCompare(b.last_name || b.username)
          if (name !== 0) return name
          return (a.first_name || '').localeCompare(b.first_name || '')
        })
        setUsers(sorted)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleRoleChange = async (userId, newRole) => {
    setFeedback(prev => ({ ...prev, [userId]: { saving: true, error: '', saved: false } }))
    try {
      const { data } = await client.patch(`/admin/users/${userId}/role/`, { user_type: newRole })
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, user_type: data.user_type } : u))
      setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: '', saved: true } }))
      setTimeout(() => setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: '', saved: false } })), 2000)
    } catch (err) {
      const msg = err?.response?.data?.error || t('admin.updateFailed')
      setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: msg, saved: false } }))
    }
  }

  if (loading) return <p className="admin-loading">{t('admin.loadingUsers')}</p>

  return (
    <div className="admin-tab-body">
      <AdminSearch value={query} onChange={onSearch} placeholder={t('admin.searchUsers')} />
      {filtered.length === 0 ? (
        <p className="admin-empty">{t('admin.noMatch')}</p>
      ) : (
      <div className="admin-users-table-wrap">
      <table className="admin-users-table">
        <thead>
          <tr>
            <th></th>
            <th>{t('admin.columnName')}</th>
            <th>{t('admin.columnUsername')}</th>
            <th>{t('admin.columnEmail')}</th>
            <th>{t('admin.columnRole')}</th>
          </tr>
        </thead>
        <tbody>
          {pageUsers.map(u => {
            const isMe = u.id === me?.id
            const fb   = feedback[u.id] || {}
            return (
              <tr key={u.id}>
                <td><div className="admin-avatar">{u.avatar_initials || '?'}</div></td>
                <td><Link className="admin-user-link" to={`/users/${u.id}`}>{u.first_name} {u.last_name}</Link></td>
                <td>@{u.username}</td>
                <td>{u.email}</td>
                <td>
                  {isMe ? (
                    <div className="admin-role-cell">
                      <select className="admin-role-select" value={u.user_type} disabled>
                        <option value="teacher">{ROLE_LABELS.teacher}</option>
                        <option value="content_creator">{ROLE_LABELS.content_creator}</option>
                        <option value="aidea_partner">{ROLE_LABELS.aidea_partner}</option>
                        <option value="admin">{ROLE_LABELS.admin}</option>
                      </select>
                      <span className="admin-you-badge">{t('admin.youBadge')}</span>
                    </div>
                  ) : (
                    <div className="admin-role-cell">
                      <select
                        className="admin-role-select"
                        value={u.user_type}
                        disabled={fb.saving}
                        onChange={e => handleRoleChange(u.id, e.target.value)}
                      >
                        <option value="teacher">{ROLE_LABELS.teacher}</option>
                        <option value="content_creator">{ROLE_LABELS.content_creator}</option>
                        <option value="aidea_partner">{ROLE_LABELS.aidea_partner}</option>
                        <option value="admin">{ROLE_LABELS.admin}</option>
                      </select>
                      {fb.saving && <span className="admin-feedback info">{t('common.saving')}</span>}
                      {fb.saved  && <span className="admin-feedback success">{t('admin.saved')}</span>}
                      {fb.error  && <span className="admin-feedback error">{fb.error}</span>}
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </div>
      )}
      <Pagination page={safePage} totalPages={totalPages} onPage={setPage} />
    </div>
  )
}

// ── Access requests tab ───────────────────────────────────────────────────────

function RequestsTab() {
  const { t } = useTranslation()
  const [requests,      setRequests]      = useState([])
  const [loading,       setLoading]       = useState(true)
  const [denyForms,     setDenyForms]     = useState({})
  const [approveErrors, setApproveErrors] = useState({})
  const [showPast,      setShowPast]      = useState(false)
  const [query,         setQuery]         = useState('')
  const [page,          setPage]          = useState(1)
  const [pastPage,      setPastPage]      = useState(1)
  const onSearch = (value) => { setQuery(value); setPage(1); setPastPage(1) }

  const fetchRequests = useCallback(async () => {
    try {
      const { data } = await client.get('/admin/access-requests/')
      setRequests(data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchRequests() }, [fetchRequests])

  const handleApprove = async (id) => {
    setApproveErrors(prev => ({ ...prev, [id]: '' }))
    try {
      const { data } = await client.patch(`/admin/access-requests/${id}/`, { action: 'approve' })
      setRequests(prev => prev.map(r => r.id === id ? { ...r, ...data } : r))
    } catch (err) {
      const msg = err?.response?.data?.error || t('admin.approveFailed')
      setApproveErrors(prev => ({ ...prev, [id]: msg }))
    }
  }

  const openDeny = (id) =>
    setDenyForms(prev => ({ ...prev, [id]: { reason: '', submitting: false, error: '' } }))

  const closeDeny = (id) =>
    setDenyForms(prev => { const n = { ...prev }; delete n[id]; return n })

  const handleDeny = async (id) => {
    const form = denyForms[id]
    if (!form?.reason?.trim()) return
    setDenyForms(prev => ({ ...prev, [id]: { ...prev[id], submitting: true, error: '' } }))
    try {
      const { data } = await client.patch(`/admin/access-requests/${id}/`, {
        action: 'deny',
        denial_reason: form.reason.trim(),
      })
      setRequests(prev => prev.map(r => r.id === id ? { ...r, ...data } : r))
      closeDeny(id)
    } catch (err) {
      const msg = err?.response?.data?.error || t('admin.denyFailed')
      setDenyForms(prev => ({ ...prev, [id]: { ...prev[id], submitting: false, error: msg } }))
    }
  }

  if (loading) return <p className="admin-loading">{t('admin.loadingRequests')}</p>

  const matched = requests.filter(r => personMatches(r, query))
  const pending = matched.filter(r => r.status === 'pending')
  const past    = matched.filter(r => r.status !== 'pending')
  const totalPages = Math.max(1, Math.ceil(pending.length / PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const pagePending = pending.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE)
  const pastTotalPages = Math.max(1, Math.ceil(past.length / PER_PAGE))
  const safePastPage = Math.min(pastPage, pastTotalPages)
  const pagePast = past.slice((safePastPage - 1) * PER_PAGE, safePastPage * PER_PAGE)

  return (
    <div className="admin-requests">
      <AdminSearch value={query} onChange={onSearch} placeholder={t('admin.searchRequests')} />

      {pending.length === 0 && <p className="admin-empty">{query.trim() ? t('admin.noMatch') : t('admin.noPendingRequests')}</p>}

      {pagePending.map(req => (
        <div key={req.id} className="admin-request-card">
          <div className="admin-request-header">
            <div className="admin-avatar">{req.avatar_initials || '?'}</div>
            <div>
              <p className="admin-request-name">{req.first_name} {req.last_name}</p>
              <p className="admin-request-meta">
                @{req.username} · {new Date(req.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <p className="admin-request-message">{req.message}</p>
          <div className="admin-request-actions">
            <button className="admin-approve-btn" onClick={() => handleApprove(req.id)}>{t('admin.approve')}</button>
            {approveErrors[req.id] && (
              <span className="admin-feedback error">{approveErrors[req.id]}</span>
            )}
            {!denyForms[req.id] ? (
              <button className="admin-deny-btn" onClick={() => openDeny(req.id)}>{t('admin.deny')}</button>
            ) : (
              <div className="admin-deny-form">
                <textarea
                  rows={3}
                  placeholder={t('admin.denyPlaceholder')}
                  value={denyForms[req.id].reason}
                  onChange={e => setDenyForms(prev => ({
                    ...prev, [req.id]: { ...prev[req.id], reason: e.target.value },
                  }))}
                />
                {denyForms[req.id].error && (
                  <p style={{ color: '#dc2626', fontSize: '0.8rem', margin: '0.25rem 0 0' }}>
                    {denyForms[req.id].error}
                  </p>
                )}
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <button
                    className="admin-deny-confirm-btn"
                    disabled={denyForms[req.id].submitting || !denyForms[req.id].reason.trim()}
                    onClick={() => handleDeny(req.id)}
                  >
                    {denyForms[req.id].submitting ? t('admin.denying') : t('admin.confirmDeny')}
                  </button>
                  <button className="admin-deny-cancel-btn" onClick={() => closeDeny(req.id)}>
                    {t('common.cancel')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}

      <Pagination page={safePage} totalPages={totalPages} onPage={setPage} />

      {past.length > 0 && (
        <div className="admin-past-section">
          <button className="admin-past-toggle" onClick={() => setShowPast(v => !v)}>
            {showPast ? '▲' : '▼'} {t('admin.pastRequests', { count: past.length })}
          </button>
          {showPast && pagePast.map(req => (
            <div key={req.id} className="admin-request-card">
              <div className="admin-request-header">
                <div className="admin-avatar">{req.avatar_initials || '?'}</div>
                <div>
                  <p className="admin-request-name">{req.first_name} {req.last_name}</p>
                  <p className="admin-request-meta">
                    @{req.username} · {new Date(req.created_at).toLocaleDateString()}
                    {' '}<span className={`admin-status-badge admin-status-${req.status}`}>{t(`admin.status.${req.status}`)}</span>
                  </p>
                </div>
              </div>
              <p className="admin-request-message">{req.message}</p>
              {req.denial_reason && (
                <p className="admin-denial-reason">{t('admin.reasonLabel', { reason: req.denial_reason })}</p>
              )}
            </div>
          ))}
          {showPast && <Pagination page={safePastPage} totalPages={pastTotalPages} onPage={setPastPage} />}
        </div>
      )}
    </div>
  )
}

// ── Onboarding translations (System tab) ───────────────────────────────────────

const ONB_POLL_MS = 3000

function OnboardingTranslationsCard() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)      // {source_language, translation_status, has_questions, languages}
  const [busyLang, setBusyLang] = useState(null)
  const [error, setError] = useState(false)

  // Initial load.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await client.get('/admin/onboarding-translations/')
        if (!cancelled) setData(res.data)
      } catch {
        if (!cancelled) setError(true)
      }
    })()
    return () => { cancelled = true }
  }, [])

  // Poll while any language is still translating.
  const anyPending = !!data && Object.values(data.translation_status || {}).includes('pending')
  useEffect(() => {
    if (!anyPending) return undefined
    const id = setInterval(async () => {
      try {
        const res = await client.get('/admin/onboarding-translations/')
        setData(res.data)
      } catch { /* keep polling */ }
    }, ONB_POLL_MS)
    return () => clearInterval(id)
  }, [anyPending])

  const translate = async (code, isRetranslate) => {
    if (isRetranslate && !window.confirm(t('admin.onboardingTr.reconfirm'))) return
    setBusyLang(code)
    try {
      const res = await client.post('/admin/onboarding-translations/', { language: code })
      setData(res.data)
    } catch { setError(true) } finally { setBusyLang(null) }
  }

  const review = async (code, reviewed) => {
    setBusyLang(code)
    try {
      const res = await client.patch('/admin/onboarding-translations/', { language: code, reviewed })
      setData(res.data)
    } catch { setError(true) } finally { setBusyLang(null) }
  }

  const statusLabel = (st) => ({
    pending:  t('authoring.translate.statusPending'),
    done:     t('authoring.translate.statusDone'),
    reviewed: t('authoring.translate.statusReviewed'),
    failed:   t('authoring.translate.statusFailed'),
  }[st] ?? t('authoring.translate.statusNone'))

  return (
    <div className="admin-system-card">
      <h2>{t('admin.onboardingTr.title')}</h2>
      <p className="admin-system-desc">{t('admin.onboardingTr.description')}</p>
      {error && !data && <span className="admin-feedback error">{t('admin.onboardingTr.loadFailed')}</span>}
      {data && !data.has_questions && (
        <span className="admin-feedback">{t('admin.onboardingTr.noQuestions')}</span>
      )}
      {data && (
        <ul className="onboarding-tr-list">
          {data.languages.map((l) => {
            const st = data.translation_status?.[l.code]
            const busy = busyLang === l.code
            const done = st === 'done' || st === 'reviewed'
            return (
              <li key={l.code} className="onboarding-tr-row">
                <span className="onboarding-tr-lang">{l.label}</span>
                <span className={`onboarding-tr-status onboarding-tr-status--${st ?? 'none'}`}>
                  {statusLabel(st)}
                </span>
                <div className="onboarding-tr-actions">
                  {st === 'done' && (
                    <button type="button" className="translation-review-btn" disabled={busy}
                            onClick={() => review(l.code, true)}>
                      {t('authoring.translate.markReviewed')}
                    </button>
                  )}
                  {st === 'reviewed' && (
                    <button type="button" className="add-dashed-btn" disabled={busy}
                            onClick={() => review(l.code, false)}>
                      {t('authoring.translate.unmarkReviewed')}
                    </button>
                  )}
                  <button
                    type="button"
                    className="add-dashed-btn"
                    disabled={busy || st === 'pending' || !data.has_questions}
                    onClick={() => translate(l.code, done)}
                  >
                    {st === 'pending'
                      ? t('authoring.translate.translating')
                      : done
                        ? t('authoring.translate.retranslate')
                        : t('admin.onboardingTr.translate')}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

// ── System tab ────────────────────────────────────────────────────────────────

function SystemTab() {
  const { t } = useTranslation()
  const [status, setStatus] = useState('idle')  // idle | queuing | queued | error

  const handleRecompute = async () => {
    setStatus('queuing')
    try {
      await client.post('/admin/recompute-recommendations/')
      setStatus('queued')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="admin-system">
      <div className="admin-system-card">
        <h2>{t('admin.djangoAdmin.title')}</h2>
        <p className="admin-system-desc">{t('admin.djangoAdmin.description')}</p>
        <a className="admin-approve-btn" href="/django-admin/">
          {t('admin.djangoAdmin.button')}
        </a>
      </div>
      <div className="admin-system-card">
        <h2>{t('admin.recompute.title')}</h2>
        <p className="admin-system-desc">{t('admin.recompute.description')}</p>
        <button
          className="admin-approve-btn"
          onClick={handleRecompute}
          disabled={status === 'queuing'}
        >
          {status === 'queuing' ? t('admin.recompute.queuing') : t('admin.recompute.button')}
        </button>
        {status === 'queued' && <span className="admin-feedback success">{t('admin.recompute.queued')}</span>}
        {status === 'error'  && <span className="admin-feedback error">{t('admin.recompute.failed')}</span>}
      </div>
      <OnboardingTranslationsCard />
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

// ── Feedback tab ──────────────────────────────────────────────────────────────

const FB_STATUSES = ['new', 'reviewing', 'in_progress', 'resolved', 'rejected']

FeedbackCard.propTypes = { item: PropTypes.object.isRequired, onStatus: PropTypes.func.isRequired }

function FeedbackCard({ item, onStatus }) {
  const { t } = useTranslation()
  // `selected` is the pending dropdown choice; it may differ from the saved
  // item.status while a rejection reason is being entered.
  const [selected, setSelected] = useState(item.status)
  const [reason, setReason] = useState(item.rejection_reason || '')
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)  // reason editor open?
  const [error, setError] = useState('')

  const commit = async (nextStatus, nextReason) => {
    setSaving(true)
    setError('')
    try {
      await onStatus(item.id, nextStatus, nextReason)
      setEditing(false)
    } catch (err) {
      setError(err?.response?.data?.detail || t('admin.updateFailed'))
      setSelected(item.status)  // revert the dropdown on failure
    } finally {
      setSaving(false)
    }
  }

  const onSelect = (value) => {
    setSelected(value)
    setError('')
    // Non-reject statuses save straight away; rejection waits for a reason.
    if (value !== 'rejected') commit(value, '')
  }

  const confirmReject = () => {
    if (!reason.trim()) {
      setError(t('admin.feedback.reasonRequired'))
      return
    }
    commit('rejected', reason.trim())
  }

  // A rejection is already on record for this item.
  const isRejected = item.status === 'rejected'
  // Show the editable reason field for a fresh rejection or when editing an existing one.
  const showReasonEditor = selected === 'rejected' && (!isRejected || editing)

  return (
    <div className="admin-fb-card">
      <div className="admin-fb-head">
        <Link className="admin-user-link" to={`/users/${item.submitter_id}`}>{item.submitter_name}</Link>
        <span className="admin-fb-cat">{item.category_label}</span>
        <span className="admin-fb-date">{new Date(item.created_at).toLocaleString()}</span>
      </div>
      <p className="admin-fb-msg">{item.message}</p>
      {item.attachments?.length > 0 && (
        <div className="admin-fb-attachments">
          {item.attachments.map((att, idx) => (
            att.type === 'image'
              ? <a key={idx} href={att.url} target="_blank" rel="noreferrer" className="admin-fb-thumb"><img src={att.url} alt={att.name || ''} /></a>
              : <a key={idx} href={att.url} target="_blank" rel="noreferrer" className="admin-fb-chip">{att.name || att.url}</a>
          ))}
        </div>
      )}
      <div className="admin-fb-controls">
        <select
          className="admin-role-select"
          value={selected}
          disabled={saving}
          onChange={(e) => onSelect(e.target.value)}
        >
          {FB_STATUSES.map(s => <option key={s} value={s}>{t(`feedback.statuses.${s}`)}</option>)}
        </select>
        {showReasonEditor && (
          <>
            <input
              className="admin-fb-reason"
              placeholder={t('admin.feedback.reasonPlaceholder')}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); confirmReject() } }}
            />
            <button
              type="button"
              className="admin-fb-reject-btn"
              onClick={confirmReject}
              disabled={saving || !reason.trim()}
            >
              {t('admin.feedback.confirmReject')}
            </button>
            {editing && (
              <button
                type="button"
                className="admin-fb-cancel-btn"
                onClick={() => { setEditing(false); setReason(item.rejection_reason || ''); setError('') }}
                disabled={saving}
              >
                {t('common.cancel')}
              </button>
            )}
          </>
        )}
        {selected === 'rejected' && isRejected && !editing && (
          <div className="admin-fb-reason-saved">
            <span className="admin-fb-reason-text">{item.rejection_reason}</span>
            <button type="button" className="admin-fb-edit-btn" onClick={() => setEditing(true)}>
              {t('admin.feedback.editReason')}
            </button>
          </div>
        )}
        {saving && <span className="admin-feedback info">{t('common.saving')}</span>}
        {error && <span className="admin-feedback error">{error}</span>}
      </div>
    </div>
  )
}

function FeedbackTab() {
  const { t } = useTranslation()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [stream, setStream] = useState('user')
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [page, setPage] = useState(1)

  useEffect(() => {
    client.get('/admin/feedback/')
      .then(res => setItems(res.data))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  const setStatus = useCallback(async (id, status, rejection_reason) => {
    const { data } = await client.patch(`/admin/feedback/${id}/`, { status, rejection_reason })
    setItems(prev => prev.map(it => it.id === id ? data : it))
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter(it =>
      it.stream === stream &&
      (statusFilter === 'all' || it.status === statusFilter) &&
      (categoryFilter === 'all' || it.category === categoryFilter) &&
      (!q || it.submitter_name.toLowerCase().includes(q)),
    )
  }, [items, stream, statusFilter, categoryFilter, query])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const pageItems = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE)

  const onFilterChange = (setter) => (val) => { setter(val); setPage(1) }

  if (loading) return <p className="admin-loading">{t('common.loading')}</p>

  return (
    <div className="admin-tab-body">
      <div className="admin-fb-streams">
        <button className={`admin-subtab ${stream === 'user' ? 'active' : ''}`} onClick={() => { setStream('user'); setPage(1) }}>
          {t('admin.feedback.userStream')}
        </button>
        <button className={`admin-subtab ${stream === 'partner' ? 'active' : ''}`} onClick={() => { setStream('partner'); setPage(1) }}>
          {t('admin.feedback.partnerStream')}
        </button>
      </div>

      <div className="admin-fb-filters">
        <AdminSearch value={query} onChange={onFilterChange(setQuery)} placeholder={t('admin.feedback.searchName')} />
        <select className="admin-role-select" value={statusFilter} onChange={(e) => onFilterChange(setStatusFilter)(e.target.value)}>
          <option value="all">{t('admin.feedback.allStatuses')}</option>
          {FB_STATUSES.map(s => <option key={s} value={s}>{t(`feedback.statuses.${s}`)}</option>)}
        </select>
        <select className="admin-role-select" value={categoryFilter} onChange={(e) => onFilterChange(setCategoryFilter)(e.target.value)}>
          <option value="all">{t('admin.feedback.allCategories')}</option>
          {['bug', 'suggestion', 'feedback', 'feature_request', 'content_issue'].map(c => (
            <option key={c} value={c}>{t(`feedback.categories.${c}`)}</option>
          ))}
        </select>
      </div>

      {pageItems.length === 0 ? (
        <p className="admin-empty">{t('admin.feedback.empty')}</p>
      ) : (
        <div className="admin-fb-list">
          {pageItems.map(it => <FeedbackCard key={it.id} item={it} onStatus={setStatus} />)}
        </div>
      )}
      <Pagination page={safePage} totalPages={totalPages} onPage={setPage} />
    </div>
  )
}

// ── Research tab (adaptive-vs-fixed study) ────────────────────────────────────

function StatTile({ label, value }) {
  return (
    <div className="admin-stat">
      <span className="admin-stat-value">{value}</span>
      <span className="admin-stat-label">{label}</span>
    </div>
  )
}
StatTile.propTypes = { label: PropTypes.string.isRequired, value: PropTypes.node.isRequired }

function ResearchTab() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    client.get('/admin/study/').then(res => setData(res.data)).catch(() => setData(null))
  }, [])

  const patch = async (body) => {
    setSaving(true)
    try {
      const res = await client.patch('/admin/study/', body)
      setData(res.data)
    } catch { /* ignore */ } finally {
      setSaving(false)
    }
  }

  const exportData = async () => {
    const res = await client.get('/admin/study/export/', { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'aidea-study-export.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!data) return <p className="admin-loading">{t('common.loading')}</p>
  const c = data.counts

  return (
    <div className="admin-tab-body">
      <div className="admin-research-controls">
        <label className="admin-toggle-row">
          <input type="checkbox" checked={data.enabled} disabled={saving}
                 onChange={(e) => patch({ enabled: e.target.checked })} />
          <span>{t('admin.research.enabled')}</span>
        </label>

        <div className="admin-research-field">
          <label>{t('admin.research.controlPath')}</label>
          <select className="admin-role-select" value={data.control_path || ''} disabled={saving}
                  onChange={(e) => patch({ control_path: e.target.value || null })}>
            <option value="">{t('admin.research.noPath')}</option>
            {data.available_paths.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>

        <label className="admin-toggle-row">
          <input type="checkbox" checked={data.post_test_open} disabled={saving}
                 onChange={(e) => patch({ post_test_open: e.target.checked })} />
          <span>{t('admin.research.postOpen')}</span>
        </label>
      </div>

      {!data.has_assessment && <p className="admin-research-warn">{t('admin.research.noAssessment')}</p>}
      {data.enabled && !data.control_path && <p className="admin-research-warn">{t('admin.research.noControlWarn')}</p>}

      <div className="admin-stats">
        <StatTile label={t('admin.research.adaptive')} value={c.adaptive} />
        <StatTile label={t('admin.research.fixed')} value={c.fixed} />
        <StatTile label={t('admin.research.preDone')} value={c.pre_done} />
        <StatTile label={t('admin.research.postDone')} value={c.post_done} />
        <StatTile label={t('admin.research.declined')} value={c.declined} />
        <StatTile label={t('admin.research.questions')} value={data.assessment_questions} />
      </div>

      <button className="admin-approve-btn admin-export-btn" onClick={exportData}>{t('admin.research.export')}</button>
    </div>
  )
}

export default function AdminPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('users')
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>{t('admin.title')}</h1>
      </div>
      <div className="admin-tabs">
        <button
          className={`admin-tab-btn ${tab === 'users' ? 'active' : ''}`}
          onClick={() => setTab('users')}
        >
          {t('admin.usersTab')}
        </button>
        <button
          className={`admin-tab-btn ${tab === 'requests' ? 'active' : ''}`}
          onClick={() => setTab('requests')}
        >
          {t('admin.requestsTab')}
        </button>
        <button
          className={`admin-tab-btn ${tab === 'feedback' ? 'active' : ''}`}
          onClick={() => setTab('feedback')}
        >
          {t('admin.feedbackTab')}
        </button>
        <button
          className={`admin-tab-btn ${tab === 'research' ? 'active' : ''}`}
          onClick={() => setTab('research')}
        >
          {t('admin.researchTab')}
        </button>
        <button
          className={`admin-tab-btn ${tab === 'system' ? 'active' : ''}`}
          onClick={() => setTab('system')}
        >
          {t('admin.systemTab')}
        </button>
      </div>
      {tab === 'users' && <UsersTab />}
      {tab === 'requests' && <RequestsTab />}
      {tab === 'feedback' && <FeedbackTab />}
      {tab === 'research' && <ResearchTab />}
      {tab === 'system' && <SystemTab />}
    </div>
  )
}
