import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
} from '../components/PasswordInput'
import { COUNTRIES, getFlagEmoji } from '../data/countries'
import './RegisterPage.css'

const GENDER_OPTIONS = [
  { value: '',        label: 'Prefer not to say' },
  { value: 'male',   label: 'Male' },
  { value: 'female', label: 'Female' },
]

export default function RegisterPage() {
  const { user, loginSession } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    first_name: '', last_name: '', username: '', email: '',
    gender: '', country: '', password: '', confirm: '',
  })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  if (user) return <Navigate to="/" replace />

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const allRulesMet    = PASSWORD_RULES.every(r => r.test(form.password))
  const passwordsMatch = form.password.length > 0 && form.password === form.confirm
  const canSubmit      =
    form.first_name && form.last_name && form.username &&
    form.email && allRulesMet && passwordsMatch && !loading

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    try {
      const { data } = await client.post('/auth/register/', {
        first_name:       form.first_name,
        last_name:        form.last_name,
        username:         form.username,
        email:            form.email,
        gender:           form.gender,
        country:          form.country,
        password:         form.password,
        confirm_password: form.confirm,
      })
      loginSession(data)
      navigate('/onboarding')
    } catch (err) {
      const detail = err?.response?.data
      if (detail && typeof detail === 'object') {
        const first = Object.values(detail)[0]
        setError(Array.isArray(first) ? first[0] : String(first))
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="register-page">
      <div className="register-card">
        <h1 className="register-title">Create your account</h1>
        <p className="register-subtitle">Join the AIDEA Teacher AI Training Platform</p>

        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="register-error">{error}</div>}

          <div className="register-name-row">
            <div className="field">
              <label htmlFor="first_name">First Name</label>
              <input
                id="first_name" type="text" value={form.first_name}
                onChange={set('first_name')} placeholder="Maria" required autoFocus
              />
            </div>
            <div className="field">
              <label htmlFor="last_name">Last Name</label>
              <input
                id="last_name" type="text" value={form.last_name}
                onChange={set('last_name')} placeholder="Papadaki" required
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="reg-username">Username</label>
            <input
              id="reg-username" type="text" value={form.username}
              onChange={set('username')} placeholder="maria.papadaki" required
              autoComplete="username"
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email" type="email" value={form.email}
              onChange={set('email')} placeholder="you@school.edu" required
              autoComplete="email"
            />
          </div>

          <div className="register-row-2">
            <div className="field">
              <label htmlFor="reg-gender">Gender</label>
              <select id="reg-gender" value={form.gender} onChange={set('gender')}>
                {GENDER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="reg-country">Country</label>
              <select id="reg-country" value={form.country} onChange={set('country')}>
                <option value="">Select country</option>
                {COUNTRIES.map(c => (
                  <option key={c.code} value={c.code}>
                    {getFlagEmoji(c.code)} {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="reg-password">Password</label>
            <PasswordInput
              value={form.password} onChange={set('password')}
              placeholder="Create a strong password" autoComplete="new-password"
            />
            <PasswordStrengthPanel password={form.password} />
          </div>

          <div className="field">
            <label htmlFor="reg-confirm">Confirm Password</label>
            <PasswordInput
              value={form.confirm} onChange={set('confirm')}
              placeholder="Repeat your password" autoComplete="new-password"
            />
            {form.confirm && (
              <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                {passwordsMatch
                  ? <><Check size={12} /> Passwords match</>
                  : <><X size={12} /> Passwords do not match</>}
              </span>
            )}
          </div>

          <button type="submit" className="register-submit" disabled={!canSubmit}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="register-link">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>

        <div className="register-footer">
          <p className="register-eu-text">
            Funded by the European Union. Views and opinions expressed are however those of the
            author(s) only and do not necessarily reflect those of the European Union or the EACEA.
          </p>
        </div>
      </div>
    </div>
  )
}
