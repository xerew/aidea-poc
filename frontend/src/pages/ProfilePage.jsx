import PropTypes from 'prop-types'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Camera, Check, X, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
} from '../components/PasswordInput'
import PreferenceFinderModal from '../components/PreferenceFinderModal'
import { useAuth } from '../context/AuthContext'
import { useAccessRequest } from '../context/AccessRequestContext'
import { COUNTRIES, getFlagEmoji } from '../data/countries'
import client from '../api/client'
import './ProfilePage.css'

function getAvatarSrc(profile) {
  if (profile?.avatar_url) return profile.avatar_url
  if (profile?.gender === 'male') return '/images/avatars/male_avatar.jpg'
  if (profile?.gender === 'female') return '/images/avatars/female_avatar.jpg'
  return null
}

function useSectionSave(endpoint, method = 'patch') {
  const { t } = useTranslation()
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
      setError(err?.response?.data?.error || t('common.saveFailed'))
    } finally {
      setSaving(false)
    }
  }, [endpoint, method, t])

  return { saving, saved, error, setError, save }
}

function SaveFeedback({ saving, saved, error, label }) {
  const { t } = useTranslation()
  return (
    <div className="profile-section-footer">
      {error && <span className="profile-feedback error">{error}</span>}
      {saved && <span className="profile-feedback success">{t('common.savedSuccess')}</span>}
      <button className="profile-save-btn" type="submit" disabled={saving}>
        {saving ? t('common.saving') : label}
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
  const { t } = useTranslation()
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '',
    subject: '', gender: '', country: '', school: '', phone: '', location: '',
  })
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/info/')

  const GENDER_OPTIONS = [
    { value: '',                label: t('profile.personalInfo.genderOptions.select') },
    { value: 'male',            label: t('profile.personalInfo.genderOptions.male') },
    { value: 'female',          label: t('profile.personalInfo.genderOptions.female') },
    { value: 'prefer_not_say',  label: t('profile.personalInfo.genderOptions.preferNotSay') },
  ]

  useEffect(() => {
    client.get('/subjects/').then(res => setSubjects(res.data)).catch(() => {})
    client.get('/profile/info/')
      .then(res => setForm(prev => ({ ...prev, ...res.data, subject: res.data.subject ?? '' })))
      .catch(() => setError(t('profile.personalInfo.loadFailed')))
      .finally(() => setLoading(false))
  }, [setError, t])

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    // The API expects a subject id or null — never an empty string.
    save({ ...form, subject: form.subject === '' ? null : form.subject })
  }

  if (loading) return <section className="profile-card"><p className="profile-loading">{t('common.loading')}</p></section>

  return (
    <section className="profile-card">
      <h2>{t('profile.personalInfo.title')}</h2>
      <form onSubmit={handleSubmit}>
        <div className="profile-grid-2">
          <div className="profile-field">
            <label>{t('profile.personalInfo.fullName')}</label>
            <div className="profile-name-row">
              <input value={form.first_name} onChange={set('first_name')} placeholder={t('profile.personalInfo.firstNamePlaceholder')} />
              <input value={form.last_name}  onChange={set('last_name')}  placeholder={t('profile.personalInfo.lastNamePlaceholder')} />
            </div>
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.email')}</label>
            <input type="email" value={form.email} onChange={set('email')} placeholder={t('profile.personalInfo.emailPlaceholder')} />
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.school')}</label>
            <input value={form.school} onChange={set('school')} placeholder={t('profile.personalInfo.schoolPlaceholder')} />
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.subjectDepartment')}</label>
            <select value={form.subject ?? ''} onChange={set('subject')}>
              <option value="">{t('profile.personalInfo.subjectOptions.select')}</option>
              {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.gender')}</label>
            <select value={form.gender} onChange={set('gender')}>
              {GENDER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.country')}</label>
            <select value={form.country} onChange={set('country')}>
              <option value="">{t('profile.personalInfo.selectCountry')}</option>
              {COUNTRIES.map(c => (
                <option key={c.code} value={c.code}>
                  {getFlagEmoji(c.code)} {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.phone')}</label>
            <input value={form.phone} onChange={set('phone')} placeholder={t('profile.personalInfo.phonePlaceholder')} />
          </div>
          <div className="profile-field">
            <label>{t('profile.personalInfo.location')}</label>
            <input value={form.location} onChange={set('location')} placeholder={t('profile.personalInfo.locationPlaceholder')} />
          </div>
        </div>
        <SaveFeedback saving={saving} saved={saved} error={error} label={t('profile.personalInfo.saveChanges')} />
      </form>
    </section>
  )
}

// ── Learning Preferences ──────────────────────────────────────────────────────

function PreferencesSection() {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    preferred_pillars: [], learning_style: '',
    weekly_learning_goal: '', email_notifications: true, progress_reminders: true,
  })
  const [loading, setLoading] = useState(true)
  const [finderOpen, setFinderOpen] = useState(false)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/preferences/')

  const PILLARS = [
    { value: 'teach-with-ai',  label: t('profile.preferences.pillars.teachWithAi') },
    { value: 'teach-for-ai',   label: t('profile.preferences.pillars.teachForAi') },
    { value: 'teach-about-ai', label: t('profile.preferences.pillars.teachAboutAi') },
  ]

  const LEARNING_FORMATS = [
    { value: '',            label: t('profile.preferences.formatOptions.select') },
    { value: 'video',       label: t('profile.preferences.formatOptions.video') },
    { value: 'text',        label: t('profile.preferences.formatOptions.text') },
    { value: 'visual',      label: t('profile.preferences.formatOptions.visual') },
    { value: 'interactive', label: t('profile.preferences.formatOptions.interactive') },
  ]

  const WEEKLY_GOALS = [
    { value: '',    label: t('profile.preferences.goalOptions.select') },
    { value: 'lt1', label: t('profile.preferences.goalOptions.lt1') },
    { value: '1_2', label: t('profile.preferences.goalOptions.1_2') },
    { value: '2_5', label: t('profile.preferences.goalOptions.2_5') },
    { value: 'gt5', label: t('profile.preferences.goalOptions.gt5') },
  ]

  useEffect(() => {
    client.get('/profile/preferences/')
      .then(res => setForm(res.data))
      .catch(() => setError(t('profile.preferences.loadFailed')))
      .finally(() => setLoading(false))
  }, [setError, t])

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

  if (loading) return <section className="profile-card"><p className="profile-loading">{t('common.loading')}</p></section>

  return (
    <section className="profile-card">
      <h2>{t('profile.preferences.title')}</h2>
      <form onSubmit={(e) => { e.preventDefault(); save(form) }}>
        <div className="profile-field">
          <label>{t('profile.preferences.preferredFormat')}</label>
          <select value={form.learning_style} onChange={set('learning_style')}>
            {LEARNING_FORMATS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <button
          type="button"
          className="profile-finder-btn"
          onClick={() => setFinderOpen(true)}
        >
          <Sparkles size={14} /> {t('profile.preferences.findPreference')}
        </button>

        <PreferenceFinderModal
          open={finderOpen}
          onClose={() => setFinderOpen(false)}
          onComplete={(style) => setForm(prev => ({ ...prev, learning_style: style }))}
        />

        <div className="profile-field">
          <label>{t('profile.preferences.preferredPillar')}</label>
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
          <label>{t('profile.preferences.weeklyGoal')}</label>
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
              <span className="toggle-title">{t('profile.preferences.emailNotifTitle')}</span>
              <span className="toggle-sub">{t('profile.preferences.emailNotifSub')}</span>
            </div>
          </label>
          <label className="profile-toggle-row">
            <input
              type="checkbox"
              checked={form.progress_reminders}
              onChange={set('progress_reminders')}
            />
            <div>
              <span className="toggle-title">{t('profile.preferences.progressRemindersTitle')}</span>
              <span className="toggle-sub">{t('profile.preferences.progressRemindersSub')}</span>
            </div>
          </label>
        </div>

        <SaveFeedback saving={saving} saved={saved} error={error} label={t('profile.preferences.savePreferences')} />
      </form>
    </section>
  )
}

// ── Privacy Settings ──────────────────────────────────────────────────────────

function PrivacySection() {
  const { t } = useTranslation()
  const [form, setForm]   = useState({ profile_public: false, share_progress: false })
  const [loading, setLoading] = useState(true)
  const { saving, saved, error, setError, save } = useSectionSave('/profile/settings/')

  useEffect(() => {
    client.get('/profile/settings/')
      .then(res => setForm(res.data))
      .catch(() => setError(t('profile.privacy.loadFailed')))
      .finally(() => setLoading(false))
  }, [setError, t])

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.checked }))

  if (loading) return <section className="profile-card"><p className="profile-loading">{t('common.loading')}</p></section>

  return (
    <section className="profile-card">
      <h2>{t('profile.privacy.title')}</h2>
      <form onSubmit={(e) => { e.preventDefault(); save(form) }}>
        <div className="profile-toggles">
          <label className="profile-toggle-row">
            <input type="checkbox" checked={form.profile_public} onChange={set('profile_public')} />
            <div>
              <span className="toggle-title">{t('profile.privacy.publicProfileTitle')}</span>
              <span className="toggle-sub">{t('profile.privacy.publicProfileSub')}</span>
            </div>
          </label>
          <label className="profile-toggle-row">
            <input type="checkbox" checked={form.share_progress} onChange={set('share_progress')} />
            <div>
              <span className="toggle-title">{t('profile.privacy.shareProgressTitle')}</span>
              <span className="toggle-sub">{t('profile.privacy.shareProgressSub')}</span>
            </div>
          </label>
        </div>
        <SaveFeedback saving={saving} saved={saved} error={error} label={t('profile.privacy.saveSettings')} />
      </form>
    </section>
  )
}

// ── Security ─────────────────────────────────────────────────────────────────

function SecuritySection() {
  const { t } = useTranslation()
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
      setError(t('profile.security.passwordRulesNotMet'))
      return
    }
    if (!passwordsMatch) {
      setError(t('profile.security.passwordsNoMatch'))
      return
    }
    setSaving(true)
    try {
      await client.post('/auth/change-password/', {
        old_password: form.old_password,
        new_password: form.new_password,
      })
      setSuccess(t('profile.security.changeSuccess'))
      setForm({ old_password: '', new_password: '', confirm: '' })
      setShowForm(false)
    } catch (err) {
      setError(err?.response?.data?.error || t('profile.security.changeFailed'))
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
      <h2>{t('profile.security.title')}</h2>

      {!showForm ? (
        <div className="profile-security-btns">
          {success && <p className="profile-feedback success">{success}</p>}
          <button className="profile-outline-btn" type="button" onClick={() => setShowForm(true)}>
            {t('profile.security.changePassword')}
          </button>
          <button
            className="profile-outline-btn"
            type="button"
            onClick={() => setTwoFaMsg(t('profile.security.twoFaComingSoon'))}
          >
            {t('profile.security.enable2fa')}
          </button>
          {twoFaMsg && <p className="profile-feedback info">{twoFaMsg}</p>}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="profile-password-form">
          <div className="profile-field">
            <label>{t('profile.security.currentPassword')}</label>
            <PasswordInput
              value={form.old_password} onChange={set('old_password')}
              placeholder={t('profile.security.currentPasswordPlaceholder')} autoComplete="current-password"
            />
          </div>

          <div className="profile-field">
            <label>{t('profile.security.newPassword')}</label>
            <PasswordInput
              value={form.new_password} onChange={set('new_password')}
              placeholder={t('profile.security.newPasswordPlaceholder')} autoComplete="new-password"
            />

            <PasswordStrengthPanel password={form.new_password} />
          </div>

          <div className="profile-field">
            <label>{t('profile.security.confirmNewPassword')}</label>
            <PasswordInput
              value={form.confirm} onChange={set('confirm')}
              placeholder={t('profile.security.confirmNewPasswordPlaceholder')} autoComplete="new-password"
            />
            {form.confirm && (
              <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                {passwordsMatch ? <><Check size={12} /> {t('auth.password.match')}</> : <><X size={12} /> {t('auth.password.noMatch')}</>}
              </span>
            )}
          </div>

          {error && <p className="profile-feedback error">{error}</p>}

          <div className="profile-section-footer">
            <button type="button" className="profile-outline-btn" onClick={cancel}>
              {t('common.cancel')}
            </button>
            <button
              className="profile-save-btn" type="submit"
              disabled={saving || !allRulesMet || !passwordsMatch}
            >
              {saving ? t('common.saving') : t('profile.security.updatePassword')}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

// ── Content Creator Access ────────────────────────────────────────────────────

function ContentCreatorAccessSection() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { request, loading, submit, cancel } = useAccessRequest()
  const [showForm,   setShowForm]   = useState(false)
  const [message,    setMessage]    = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error,      setError]      = useState('')

  // #7: any user without creator/admin access may request it (not just teachers).
  if (['content_creator', 'admin'].includes(user?.profile?.user_type)) return null

  if (loading) {
    return (
      <section className="profile-card">
        <h2>{t('profile.contentCreator.title')}</h2>
        <p className="profile-loading">{t('common.loading')}</p>
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
      setError(err?.response?.data?.error || t('profile.contentCreator.submitFailed'))
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
        <label htmlFor="cc-message">{t('profile.contentCreator.why')}</label>
        <textarea
          id="cc-message"
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder={t('profile.contentCreator.describePlaceholder')}
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
          {t('common.cancel')}
        </button>
        <button
          type="submit"
          className="profile-save-btn"
          disabled={submitting || !message.trim()}
        >
          {submitting ? t('profile.contentCreator.submitting') : t('profile.contentCreator.submitRequest')}
        </button>
      </div>
    </form>
  )

  return (
    <section className="profile-card">
      <h2>{t('profile.contentCreator.title')}</h2>

      {!request && !showForm && (
        <>
          <p className="profile-loading">
            {t('profile.contentCreator.prompt')}
          </p>
          <button
            className="profile-outline-btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setShowForm(true)}
          >
            {t('profile.contentCreator.requestAccess')}
          </button>
        </>
      )}

      {!request && showForm && requestForm}

      {request?.status === 'pending' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span className="cc-badge cc-badge-pending">{t('profile.contentCreator.pendingReview')}</span>
            <span className="profile-loading">
              {t('profile.contentCreator.submittedOn', { date: new Date(request.created_at).toLocaleDateString() })}
            </span>
          </div>
          <button className="profile-outline-btn" onClick={handleCancel}>
            {t('profile.contentCreator.cancelRequest')}
          </button>
        </>
      )}

      {request?.status === 'denied' && (
        <>
          <div className="cc-denial-box">
            <p className="cc-denial-label">{t('profile.contentCreator.denied')}</p>
            <p className="cc-denial-reason">{request.denial_reason}</p>
          </div>
          {!showForm ? (
            <button
              className="profile-outline-btn"
              style={{ marginTop: '1rem' }}
              onClick={() => setShowForm(true)}
            >
              {t('profile.contentCreator.requestAgain')}
            </button>
          ) : (
            <div style={{ marginTop: '1rem' }}>{requestForm}</div>
          )}
        </>
      )}
    </section>
  )
}

// ── AI competency ─────────────────────────────────────────────────────────────

const COMPETENCY_MAX = 6

function competencyLevel(score) {
  if (score <= 2) return { key: 'beginner', cls: 'beginner' }
  if (score <= 4) return { key: 'intermediate', cls: 'intermediate' }
  return { key: 'advanced', cls: 'advanced' }
}

function CompetencyBadge() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const profile = user?.profile
  if (profile?.competency_score == null) return null

  const score = profile.competency_score
  const level = competencyLevel(score)

  return (
    <div className="profile-competency" title={t('profile.competency.tooltip')}>
      <div className="profile-competency-row">
        <span className={`profile-competency-badge profile-competency-badge--${level.cls}`}>
          {t(`profile.competency.${level.key}`)}
        </span>
        <span className="profile-competency-score">
          {t('profile.competency.label', { score, max: COMPETENCY_MAX })}
        </span>
      </div>
      <div className="profile-competency-bar">
        <div
          className="profile-competency-fill"
          style={{ width: `${(score / COMPETENCY_MAX) * 100}%` }}
        />
      </div>
    </div>
  )
}

// ── Avatar with upload ────────────────────────────────────────────────────────

function ProfileAvatar() {
  const { t } = useTranslation()
  const { user, updateUser } = useAuth()
  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const avatarSrc = getAvatarSrc(user?.profile)

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const form = new FormData()
      form.append('avatar', file)
      const { data } = await client.post('/profile/avatar/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      updateUser({ profile: data.profile })
    } catch {
      setError(t('profile.avatar.uploadFailed'))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleRemove = async () => {
    setUploading(true)
    setError('')
    try {
      const { data } = await client.delete('/profile/avatar/')
      updateUser({ profile: data.profile })
    } catch {
      setError(t('profile.avatar.removeFailed'))
    } finally {
      setUploading(false)
    }
  }

  if (!user) return null

  return (
    <div className="profile-identity">
      <div className="profile-avatar-wrap">
        {avatarSrc ? (
          <img className="profile-avatar-img" src={avatarSrc} alt={t('profile.avatar.alt')} />
        ) : (
          <div className="profile-avatar">{user.profile?.avatar_initials || '?'}</div>
        )}
        <button
          type="button"
          className="profile-avatar-upload-btn"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          title={t('profile.avatar.changePhoto')}
        >
          <Camera size={14} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="profile-avatar-file-input"
          onChange={handleFileChange}
        />
      </div>
      <div>
        <p className="profile-name">{user.first_name} {user.last_name}</p>
        <p className="profile-username">@{user.username}</p>
        <CompetencyBadge />
        {user.profile?.avatar_url && (
          <button
            type="button"
            className="profile-avatar-remove-btn"
            onClick={handleRemove}
            disabled={uploading}
          >
            {uploading ? t('profile.avatar.removing') : t('profile.avatar.removePhoto')}
          </button>
        )}
        {uploading && !user.profile?.avatar_url && (
          <span className="profile-loading">{t('profile.avatar.uploading')}</span>
        )}
        {error && <span className="profile-feedback error">{error}</span>}
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { t } = useTranslation()
  return (
    <div className="profile-page">
      <div className="profile-page-header">
        <h1>{t('profile.title')}</h1>
        <p className="profile-page-sub">{t('profile.subtitle')}</p>
      </div>

      <ProfileAvatar />
      <PersonalInfoSection />
      <PreferencesSection />
      <PrivacySection />
      <SecuritySection />
      <ContentCreatorAccessSection />
    </div>
  )
}
