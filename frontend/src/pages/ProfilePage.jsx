import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './ProfilePage.css'

const PILLARS = [
  { value: 'teach-with-ai',  label: 'Teach with AI' },
  { value: 'teach-for-ai',   label: 'Teach for AI' },
  { value: 'teach-about-ai', label: 'Teach about AI' },
]

const LEARNING_STYLES = [
  { value: 'video',       label: 'Video' },
  { value: 'text',        label: 'Text / Reading' },
  { value: 'visual',      label: 'Visual (slides, diagrams)' },
  { value: 'interactive', label: 'Interactive (quizzes, exercises)' },
]

export default function ProfilePage() {
  const { user } = useAuth()
  const [pillars, setPillars]   = useState([])
  const [style, setStyle]       = useState('')
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState('')

  useEffect(() => {
    client.get('/profile/preferences/')
      .then((res) => {
        setPillars(res.data.preferred_pillars ?? [])
        setStyle(res.data.learning_style ?? '')
      })
      .catch(() => setError('Failed to load preferences.'))
      .finally(() => setLoading(false))
  }, [])

  const togglePillar = (val) => {
    setSaved(false)
    setPillars((prev) =>
      prev.includes(val) ? prev.filter((p) => p !== val) : [...prev, val],
    )
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await client.patch('/profile/preferences/', {
        preferred_pillars: pillars,
        learning_style: style,
      })
      setSaved(true)
    } catch {
      setError('Failed to save preferences.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="profile-page">
      <h1 className="profile-heading">Profile</h1>

      {user && (
        <div className="profile-identity">
          <div className="profile-avatar">{user.profile?.avatar_initials || '?'}</div>
          <div>
            <p className="profile-name">{user.first_name} {user.last_name}</p>
            <p className="profile-username">@{user.username}</p>
          </div>
        </div>
      )}

      <section className="prefs-section">
        <h2>Learning Preferences</h2>
        <p className="prefs-hint">
          These preferences personalise your &ldquo;Recommended for you&rdquo; course list.
        </p>

        {loading ? (
          <p className="prefs-loading">Loading…</p>
        ) : (
          <>
            <div className="prefs-group">
              <h3>AI Learning Pillars</h3>
              <p className="prefs-sub">Select the pillars you want to focus on.</p>
              {PILLARS.map(({ value, label }) => (
                <label key={value} className="prefs-checkbox-label">
                  <input
                    type="checkbox"
                    checked={pillars.includes(value)}
                    onChange={() => togglePillar(value)}
                  />
                  {label}
                </label>
              ))}
            </div>

            <div className="prefs-group">
              <h3>Preferred Learning Style</h3>
              <p className="prefs-sub">How do you learn best?</p>
              {LEARNING_STYLES.map(({ value, label }) => (
                <label key={value} className="prefs-radio-label">
                  <input
                    type="radio"
                    name="learning_style"
                    value={value}
                    checked={style === value}
                    onChange={() => { setSaved(false); setStyle(value) }}
                  />
                  {label}
                </label>
              ))}
            </div>

            {error && <p className="prefs-error">{error}</p>}
            {saved && <p className="prefs-success">Preferences saved! Your recommendations will update shortly.</p>}

            <button
              className="prefs-save-btn"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save Preferences'}
            </button>
          </>
        )}
      </section>
    </div>
  )
}
