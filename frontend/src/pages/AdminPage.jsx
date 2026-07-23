import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './AdminPage.css'


// ── Users tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { t } = useTranslation()
  const { user: me } = useAuth()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [feedback, setFeedback] = useState({})

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
          {users.map(u => {
            const isMe = u.id === me?.id
            const fb   = feedback[u.id] || {}
            return (
              <tr key={u.id}>
                <td><div className="admin-avatar">{u.avatar_initials || '?'}</div></td>
                <td>{u.first_name} {u.last_name}</td>
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

  const pending = requests.filter(r => r.status === 'pending')
  const past    = requests.filter(r => r.status !== 'pending')

  return (
    <div className="admin-requests">
      {pending.length === 0 && <p className="admin-empty">{t('admin.noPendingRequests')}</p>}

      {pending.map(req => (
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

      {past.length > 0 && (
        <div className="admin-past-section">
          <button className="admin-past-toggle" onClick={() => setShowPast(v => !v)}>
            {showPast ? '▲' : '▼'} {t('admin.pastRequests', { count: past.length })}
          </button>
          {showPast && past.map(req => (
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
        </div>
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
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

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
          className={`admin-tab-btn ${tab === 'system' ? 'active' : ''}`}
          onClick={() => setTab('system')}
        >
          {t('admin.systemTab')}
        </button>
      </div>
      {tab === 'users' && <UsersTab />}
      {tab === 'requests' && <RequestsTab />}
      {tab === 'system' && <SystemTab />}
    </div>
  )
}
