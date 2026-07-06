import PropTypes from 'prop-types'
import { useCallback, useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
} from '../components/PasswordInput'
import { useAuth } from '../context/AuthContext'
import { useAccessRequest } from '../context/AccessRequestContext'
import client from '../api/client'
import './ProfilePage.css'

const PILLARS = [
  { value: 'teach-with-ai',  label: 'Teach with AI' },
  { value: 'teach-for-ai',   label: 'Teach for AI' },
  { value: 'teach-about-ai', label: 'Teach about AI' },
]

const SUBJECT_AREAS = [
  { value: '',           label: 'Select subject area' },
  { value: 'stem',       label: 'STEM' },
  { value: 'humanities', label: 'Humanities' },
  { value: 'languages',  label: 'Languages' },
  { value: 'arts',       label: 'Arts' },
  { value: 'general',    label: 'General / Multiple' },
]

const LEARNING_FORMATS = [
  { value: '',            label: 'Select format' },
  { value: 'video',       label: 'Video-based' },
  { value: 'text',        label: 'Text / Reading' },
  { value: 'visual',      label: 'Visual (slides, diagrams)' },
  { value: 'interactive', label: 'Interactive (quizzes, exercises)' },
]

const WEEKLY_GOALS = [
  { value: '',    label: 'Select goal' },
  { value: 'lt1', label: 'Under 1 hour' },
  { value: '1_2', label: '1-2 hours' },
  { value: '2_5', label: '2-5 hours' },
  { value: 'gt5', label: '5+ hours' },
]

function useSectionSave(endpoint, method = 'patch') {
  const [saving, setSaving] = useState(false)
  const [saved,  setSaved]  = useState(false)
  const [error,  setError]  = useState('')

  const save = useCallback(async (data) => {
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await client[method](endpoint, data)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to save.')
    } finally {
      setSaving(false)
    }
  }, [endpoint, method])

  return { saving, saved, error, setError, save }
}

function SaveFeedback({ saving, saved, error, label = 'Save' }) {
  return (
    <div className="profile-section-footer">
      {error && <span className="profile-feedback error">{error}</span>}
      {saved && <span className="profile-feedback success">Saved successfully.</span>}
      <button className="profile-save-btn" type="submit" disabled={saving}>
        {saving ? 'Saving…' : label}
      </button>
    </div>
  )
}

SaveFeedback.propTypes = {
  saving: PropTypes.bool.isRequired,
  saved:  PropTypes.bool.isRequired,
  error:  PropTypes.string.isRequired,
  label:  PropTypes.string,
}

// ── Personal Information ──────────────────────────────────────────────────────

function PersonalInfoSection() {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '',
    subject_area: '', school: '', phone: '', location: '',
  })
  const [loading, setLoading] = useState(true)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/info/')

  useEffect(() => {
    client.get('/profile/info/')
      .then(res => setForm(res.data))
      .catch(() => setError('Failed to load profile.'))
      .finally(() => setLoading(false))
  }, [setError])

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    save(form)
  }

  if (loading) return <section className="profile-card"><p className="profile-loading">Loading…</p></section>

  return (
    <section className="profile-card">
      <h2>Personal Information</h2>
      <form onSubmit={handleSubmit}>
        <div className="profile-grid-2">
          <div className="profile-field">
            <label>Full Name</label>
            <div className="profile-name-row">
              <input value={form.first_name} onChange={set('first_name')} placeholder="First name" />
              <input value={form.last_name}  onChange={set('last_name')}  placeholder="Last name" />
            </div>
          </div>
          <div className="profile-field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" />
          </div>
          <div className="profile-field">
            <label>School / Institution</label>
            <input value={form.school} onChange={set('school')} placeholder="Your school or institution" />
          </div>
          <div className="profile-field">
            <label>Subject / Department</label>
            <select value={form.subject_area} onChange={set('subject_area')}>
              {SUBJECT_AREAS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="profile-field">
            <label>Phone Number</label>
            <input value={form.phone} onChange={set('phone')} placeholder="+30 210 000 0000" />
          </div>
          <div className="profile-field">
            <label>Location</label>
            <input value={form.location} onChange={set('location')} placeholder="City, Country" />
          </div>
        </div>
        <SaveFeedback saving={saving} saved={saved} error={error} label="Save Changes" />
      </form>
    </section>
  )
}

// ── Learning Preferences ──────────────────────────────────────────────────────

function PreferencesSection() {
  const [form, setForm] = useState({
    preferred_pillars: [], learning_style: '',
    weekly_learning_goal: '', email_notifications: true, progress_reminders: true,
  })
  const [loading, setLoading] = useState(true)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/preferences/')

  useEffect(() => {
    client.get('/profile/preferences/')
      .then(res => setForm(res.data))
      .catch(() => setError('Failed to load preferences.'))
      .finally(() => setLoading(false))
  }, [setError])

  const togglePillar = (val) =>
    setForm(prev => ({
      ...prev,
      preferred_pillars: prev.preferred_pillars.includes(val)
        ? prev.preferred_pillars.filter(p => p !== val)
        : [...prev.preferred_pillars, val],
    }))

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm(prev => ({ ...prev, [key]: value }))
  }

  if (loading) return <section className="profile-card"><p className="profile-loading">Loading…</p></section>

  return (
    <section className="profile-card">
      <h2>Learning Preferences</h2>
      <form onSubmit={(e) => { e.preventDefault(); save(form) }}>
        <div className="profile-field">
          <label>Preferred Learning Format</label>
          <select value={form.learning_style} onChange={set('learning_style')}>
            {LEARNING_FORMATS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="profile-field">
          <label>Preferred Pillar</label>
          <div className="profile-pill-group">
            {PILLARS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`profile-pill ${form.preferred_pillars.includes(value) ? 'active' : ''}`}
                onClick={() => togglePillar(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="profile-field">
          <label>Weekly Learning Goal</label>
          <select value={form.weekly_learning_goal} onChange={set('weekly_learning_goal')}>
            {WEEKLY_GOALS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="profile-toggles">
          <label className="profile-toggle-row">
            <input
              type="checkbox"
              checked={form.email_notifications}
              onChange={set('email_notifications')}
            />
            <div>
              <span className="toggle-title">Email notifications for new courses</span>
              <span className="toggle-sub">Receive updates about new AI courses and content</span>
            </div>
          </label>
          <label className="profile-toggle-row">
            <input
              type="checkbox"
              checked={form.progress_reminders}
              onChange={set('progress_reminders')}
            />
            <div>
              <span className="toggle-title">Progress reminders</span>
              <span className="toggle-sub">Get weekly reminders to continue your learning</span>
            </div>
          </label>
        </div>

        <SaveFeedback saving={saving} saved={saved} error={error} label="Save Preferences" />
      </form>
    </section>
  )
}

// ── Privacy Settings ──────────────────────────────────────────────────────────

function PrivacySection() {
  const [form, setForm]   = useState({ profile_public: false, share_progress: false })
  const [loading, setLoading] = useState(true)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/settings/')

  useEffect(() => {
    client.get('/profile/settings/')
      .then(res => setForm(res.data))
      .catch(() => setError('Failed to load settings.'))
      .finally(() => setLoading(false))
  }, [setError])

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.checked }))

  if (loading) return <section className="profile-card"><p className="profile-loading">Loading…</p></section>

  return (
    <section className="profile-card">
      <h2>Privacy Settings</h2>
      <form onSubmit={(e) => { e.preventDefault(); save(form) }}>
        <div className="profile-toggles">
          <label className="profile-toggle-row">
            <input type="checkbox" checked={form.profile_public} onChange={set('profile_public')} />
            <div>
              <span className="toggle-title">Make profile public</span>
              <span className="toggle-sub">Allow other educators to view your profile</span>
            </div>
          </label>
          <label className="profile-toggle-row">
            <input type="checkbox" checked={form.share_progress} onChange={set('share_progress')} />
            <div>
              <span className="toggle-title">Share learning progress</span>
              <span className="toggle-sub">Display your course progress on your profile</span>
            </div>
          </label>
        </div>
        <SaveFeedback saving={saving} saved={saved} error={error} label="Save Settings" />
      </form>
    </section>
  )
}

// ── Security ─────────────────────────────────────────────────────────────────

function SecuritySection() {
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm: '' })
  const [saving, setSaving]   = useState(false)
  const [success, setSuccess] = useState('')
  const [error,   setError]   = useState('')
  const [twoFaMsg, setTwoFaMsg] = useState('')

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const allRulesMet = PASSWORD_RULES.every(r => r.test(form.new_password))
  const passwordsMatch = form.new_password && form.confirm && form.new_password === form.confirm

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (!allRulesMet) {
      setError('Password does not meet all requirements.')
      return
    }
    if (!passwordsMatch) {
      setError('New passwords do not match.')
      return
    }
    setSaving(true)
    try {
      await client.post('/auth/change-password/', {
        old_password: form.old_password,
        new_password: form.new_password,
      })
      setSuccess('Password changed successfully.')
      setForm({ old_password: '', new_password: '', confirm: '' })
      setShowForm(false)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to change password.')
    } finally {
      setSaving(false)
    }
  }

  const cancel = () => {
    setShowForm(false)
    setError('')
    setForm({ old_password: '', new_password: '', confirm: '' })
  }

  return (
    <section className="profile-card">
      <h2>Security</h2>

      {!showForm ? (
        <div className="profile-security-btns">
          {success && <p className="profile-feedback success">{success}</p>}
          <button className="profile-outline-btn" type="button" onClick={() => setShowForm(true)}>
            Change Password
          </button>
          <button
            className="profile-outline-btn"
            type="button"
            onClick={() => setTwoFaMsg('Two-factor authentication is coming soon.')}
          >
            Enable Two-Factor Authentication
          </button>
          {twoFaMsg && <p className="profile-feedback info">{twoFaMsg}</p>}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="profile-password-form">
          <div className="profile-field">
            <label>Current Password</label>
            <PasswordInput
              value={form.old_password} onChange={set('old_password')}
              placeholder="Enter current password" autoComplete="current-password"
            />
          </div>

          <div className="profile-field">
            <label>New Password</label>
            <PasswordInput
              value={form.new_password} onChange={set('new_password')}
              placeholder="Create a strong password" autoComplete="new-password"
            />

            <PasswordStrengthPanel password={form.new_password} />
          </div>

          <div className="profile-field">
            <label>Confirm New Password</label>
            <PasswordInput
              value={form.confirm} onChange={set('confirm')}
              placeholder="Repeat new password" autoComplete="new-password"
            />
            {form.confirm && (
              <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                {passwordsMatch ? <><Check size={12} /> Passwords match</> : <><X size={12} /> Passwords do not match</>}
              </span>
            )}
          </div>

          {error && <p className="profile-feedback error">{error}</p>}

          <div className="profile-section-footer">
            <button type="button" className="profile-outline-btn" onClick={cancel}>
              Cancel
            </button>
            <button
              className="profile-save-btn" type="submit"
              disabled={saving || !allRulesMet || !passwordsMatch}
            >
              {saving ? 'Saving…' : 'Update Password'}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

// ── Content Creator Access ────────────────────────────────────────────────────

function ContentCreatorAccessSection() {
  const { user } = useAuth()
  const { request, loading, submit, cancel } = useAccessRequest()
  const [showForm,   setShowForm]   = useState(false)
  const [message,    setMessage]    = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error,      setError]      = useState('')

  if (user?.profile?.user_type !== 'teacher') return null

  if (loading) {
    return (
      <section className="profile-card">
        <h2>Content Creator Access</h2>
        <p className="profile-loading">Loading…</p>
      </section>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim()) return
    setSubmitting(true)
    setError('')
    try {
      await submit(message.trim())
      setShowForm(false)
      setMessage('')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to submit request.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async () => {
    try { await cancel(request.id) } catch { /* ignore */ }
  }

  const requestForm = (
    <form onSubmit={handleSubmit}>
      <div className="profile-field">
        <label htmlFor="cc-message">Why do you want Content Creator access?</label>
        <textarea
          id="cc-message"
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder="Describe your plans for creating courses…"
          rows={4}
          required
        />
      </div>
      {error && <p className="profile-feedback error">{error}</p>}
      <div className="profile-section-footer">
        <button
          type="button"
          className="profile-outline-btn"
          onClick={() => { setShowForm(false); setMessage('') }}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="profile-save-btn"
          disabled={submitting || !message.trim()}
        >
          {submitting ? 'Submitting…' : 'Submit Request'}
        </button>
      </div>
    </form>
  )

  return (
    <section className="profile-card">
      <h2>Content Creator Access</h2>

      {!request && !showForm && (
        <>
          <p className="profile-loading">
            Want to create and publish courses? Request access from the admin team.
          </p>
          <button
            className="profile-outline-btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setShowForm(true)}
          >
            Request Access
          </button>
        </>
      )}

      {!request && showForm && requestForm}

      {request?.status === 'pending' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span className="cc-badge cc-badge-pending">Pending Review</span>
            <span className="profile-loading">
              Submitted {new Date(request.created_at).toLocaleDateString()}
            </span>
          </div>
          <button className="profile-outline-btn" onClick={handleCancel}>
            Cancel Request
          </button>
        </>
      )}

      {request?.status === 'denied' && (
        <>
          <div className="cc-denial-box">
            <p className="cc-denial-label">Your request was denied</p>
            <p className="cc-denial-reason">{request.denial_reason}</p>
          </div>
          {!showForm ? (
            <button
              className="profile-outline-btn"
              style={{ marginTop: '1rem' }}
              onClick={() => setShowForm(true)}
            >
              Request Again
            </button>
          ) : (
            <div style={{ marginTop: '1rem' }}>{requestForm}</div>
          )}
        </>
      )}
    </section>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { user } = useAuth()

  return (
    <div className="profile-page">
      <div className="profile-page-header">
        <h1>Profile</h1>
        <p className="profile-page-sub">Manage your account settings and preferences</p>
      </div>

      {user && (
        <div className="profile-identity">
          <div className="profile-avatar">{user.profile?.avatar_initials || '?'}</div>
          <div>
            <p className="profile-name">{user.first_name} {user.last_name}</p>
            <p className="profile-username">@{user.username}</p>
          </div>
        </div>
      )}

      <PersonalInfoSection />
      <PreferencesSection />
      <PrivacySection />
      <SecuritySection />
      <ContentCreatorAccessSection />
    </div>
  )
}
