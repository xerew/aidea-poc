import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './AdminPage.css'

const ROLE_LABELS = {
  teacher:         'Teacher',
  content_creator: 'Content Creator',
  admin:           'Admin',
}

// ── Users tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { user: me } = useAuth()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [feedback, setFeedback] = useState({})

  useEffect(() => {
    client.get('/admin/users/')
      .then(({ data }) => {
        const ROLE_ORDER = { admin: 0, content_creator: 1, teacher: 2 }
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
      const msg = err?.response?.data?.error || 'Failed to update.'
      setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: msg, saved: false } }))
    }
  }

  if (loading) return <p className="admin-loading">Loading users…</p>

  return (
    <div className="admin-users-table-wrap">
      <table className="admin-users-table">
        <thead>
          <tr>
            <th></th>
            <th>Name</th>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
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
                        <option value="teacher">Teacher</option>
                        <option value="content_creator">Content Creator</option>
                        <option value="admin">Admin</option>
                      </select>
                      <span className="admin-you-badge">You</span>
                    </div>
                  ) : (
                    <div className="admin-role-cell">
                      <select
                        className="admin-role-select"
                        value={u.user_type}
                        disabled={fb.saving}
                        onChange={e => handleRoleChange(u.id, e.target.value)}
                      >
                        <option value="teacher">Teacher</option>
                        <option value="content_creator">Content Creator</option>
                        <option value="admin">Admin</option>
                      </select>
                      {fb.saving && <span className="admin-feedback info">Saving…</span>}
                      {fb.saved  && <span className="admin-feedback success">✓ Saved</span>}
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
      const msg = err?.response?.data?.error || 'Failed to approve.'
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
      const msg = err?.response?.data?.error || 'Failed to deny.'
      setDenyForms(prev => ({ ...prev, [id]: { ...prev[id], submitting: false, error: msg } }))
    }
  }

  if (loading) return <p className="admin-loading">Loading requests…</p>

  const pending = requests.filter(r => r.status === 'pending')
  const past    = requests.filter(r => r.status !== 'pending')

  return (
    <div className="admin-requests">
      {pending.length === 0 && <p className="admin-empty">No pending requests.</p>}

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
            <button className="admin-approve-btn" onClick={() => handleApprove(req.id)}>Approve</button>
            {approveErrors[req.id] && (
              <span className="admin-feedback error">{approveErrors[req.id]}</span>
            )}
            {!denyForms[req.id] ? (
              <button className="admin-deny-btn" onClick={() => openDeny(req.id)}>Deny</button>
            ) : (
              <div className="admin-deny-form">
                <textarea
                  rows={3}
                  placeholder="Explain why this request is denied…"
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
                    {denyForms[req.id].submitting ? 'Denying…' : 'Confirm Deny'}
                  </button>
                  <button className="admin-deny-cancel-btn" onClick={() => closeDeny(req.id)}>
                    Cancel
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
            {showPast ? '▲' : '▼'} Past Requests ({past.length})
          </button>
          {showPast && past.map(req => (
            <div key={req.id} className="admin-request-card">
              <div className="admin-request-header">
                <div className="admin-avatar">{req.avatar_initials || '?'}</div>
                <div>
                  <p className="admin-request-name">{req.first_name} {req.last_name}</p>
                  <p className="admin-request-meta">
                    @{req.username} · {new Date(req.created_at).toLocaleDateString()}
                    {' '}<span className={`admin-status-badge admin-status-${req.status}`}>{req.status}</span>
                  </p>
                </div>
              </div>
              <p className="admin-request-message">{req.message}</p>
              {req.denial_reason && (
                <p className="admin-denial-reason">Reason: {req.denial_reason}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab, setTab] = useState('users')
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Admin Panel</h1>
      </div>
      <div className="admin-tabs">
        <button
          className={`admin-tab-btn ${tab === 'users' ? 'active' : ''}`}
          onClick={() => setTab('users')}
        >
          Users
        </button>
        <button
          className={`admin-tab-btn ${tab === 'requests' ? 'active' : ''}`}
          onClick={() => setTab('requests')}
        >
          Access Requests
        </button>
      </div>
      {tab === 'users' ? <UsersTab /> : <RequestsTab />}
    </div>
  )
}
