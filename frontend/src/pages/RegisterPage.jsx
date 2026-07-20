import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import LanguageSwitcher from '../components/LanguageSwitcher'
import client from '../api/client'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
} from '../components/PasswordInput'
import { COUNTRIES, getFlagEmoji } from '../data/countries'
import './RegisterPage.css'

export default function RegisterPage() {
  const { t } = useTranslation()
  const { user, loginSession } = useAuth()
  const navigate = useNavigate()

  const GENDER_OPTIONS = [
    { value: '',       label: t('auth.register.genderOptions.notSay') },
    { value: 'male',   label: t('auth.register.genderOptions.male') },
    { value: 'female', label: t('auth.register.genderOptions.female') },
  ]

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
        setError(t('auth.register.genericError'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="register-page">
      <div className="register-card">
        <div className="register-lang-switcher">
          <LanguageSwitcher />
        </div>
        <h1 className="register-title">{t('auth.register.title')}</h1>
        <p className="register-subtitle">{t('auth.register.subtitle')}</p>

        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="register-error">{error}</div>}

          <div className="register-name-row">
            <div className="field">
              <label htmlFor="first_name">{t('auth.register.firstName')}</label>
              <input
                id="first_name" type="text" value={form.first_name}
                onChange={set('first_name')} placeholder={t('auth.register.firstNamePlaceholder')} required autoFocus
              />
            </div>
            <div className="field">
              <label htmlFor="last_name">{t('auth.register.lastName')}</label>
              <input
                id="last_name" type="text" value={form.last_name}
                onChange={set('last_name')} placeholder={t('auth.register.lastNamePlaceholder')} required
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="reg-username">{t('auth.register.username')}</label>
            <input
              id="reg-username" type="text" value={form.username}
              onChange={set('username')} placeholder={t('auth.register.usernamePlaceholder')} required
              autoComplete="username"
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">{t('auth.register.email')}</label>
            <input
              id="reg-email" type="email" value={form.email}
              onChange={set('email')} placeholder={t('auth.register.emailPlaceholder')} required
              autoComplete="email"
            />
          </div>

          <div className="register-row-2">
            <div className="field">
              <label htmlFor="reg-gender">{t('auth.register.gender')}</label>
              <select id="reg-gender" value={form.gender} onChange={set('gender')}>
                {GENDER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="reg-country">{t('auth.register.country')}</label>
              <select id="reg-country" value={form.country} onChange={set('country')}>
                <option value="">{t('auth.register.selectCountry')}</option>
                {COUNTRIES.map(c => (
                  <option key={c.code} value={c.code}>
                    {getFlagEmoji(c.code)} {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="reg-password">{t('auth.register.password')}</label>
            <PasswordInput
              value={form.password} onChange={set('password')}
              placeholder={t('auth.register.passwordPlaceholder')} autoComplete="new-password"
            />
            <PasswordStrengthPanel password={form.password} />
          </div>

          <div className="field">
            <label htmlFor="reg-confirm">{t('auth.register.confirmPassword')}</label>
            <PasswordInput
              value={form.confirm} onChange={set('confirm')}
              placeholder={t('auth.register.confirmPasswordPlaceholder')} autoComplete="new-password"
            />
            {form.confirm && (
              <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                {passwordsMatch
                  ? <><Check size={12} /> {t('auth.password.match')}</>
                  : <><X size={12} /> {t('auth.password.noMatch')}</>}
              </span>
            )}
          </div>

          <button type="submit" className="register-submit" disabled={!canSubmit}>
            {loading ? t('auth.register.submitting') : t('auth.register.submit')}
          </button>
        </form>

        <p className="register-link">
          {t('auth.register.haveAccount')} <Link to="/login">{t('auth.register.signIn')}</Link>
        </p>

        <div className="register-footer">
          <p className="register-eu-text">
            {t('common.euFundedShort')}
          </p>
        </div>
      </div>
    </div>
  )
}
