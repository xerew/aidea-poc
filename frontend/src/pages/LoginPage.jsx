import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import LanguageSwitcher from '../components/LanguageSwitcher'
import './LoginPage.css'

export default function LoginPage() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError(t('auth.login.invalidCredentials'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-lang-switcher">
          <LanguageSwitcher />
        </div>
        <img
          src="/images/logos/aidea-logo.png"
          alt="AIDEA"
          className="login-logo"
        />
        <p className="login-subtitle">{t('auth.login.subtitle')}</p>

        <form onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}
          <div className="field">
            <label htmlFor="username">{t('auth.login.usernameLabel')}</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">{t('auth.login.passwordLabel')}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? t('auth.login.signingIn') : t('auth.login.signIn')}
          </button>
        </form>

        <p className="login-signup-link">
          {t('auth.login.noAccount')} <Link to="/register">{t('auth.login.createAccount')}</Link>
        </p>

        <div className="login-footer">
          <img
            src="/images/logos/eu-cofunded.webp"
            alt={t('common.euCofundedAlt')}
            className="login-eu-logo"
          />
          <p className="login-eu-text">
            {t('common.euFundedShort')}
          </p>
        </div>
      </div>
    </div>
  )
}
