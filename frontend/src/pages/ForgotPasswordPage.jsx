import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import client from '../api/client'
import './LoginPage.css'

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await client.post('/auth/password-reset/', { email })
    } catch { /* response is intentionally identical either way */ }
    setSent(true)
    setLoading(false)
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-lang-switcher">
          <LanguageSwitcher />
        </div>
        <img src="/images/logos/aidea-logo.png" alt="AIDEA" className="login-logo" />
        <p className="login-subtitle">{t('auth.forgot.subtitle')}</p>

        {sent ? (
          <>
            <p className="login-info">{t('auth.forgot.sent')}</p>
            <p className="login-signup-link"><Link to="/login">{t('auth.forgot.backToLogin')}</Link></p>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="email">{t('auth.forgot.emailLabel')}</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button type="submit" disabled={loading || !email}>
              {loading ? t('auth.forgot.sending') : t('auth.forgot.sendLink')}
            </button>
            <p className="login-signup-link"><Link to="/login">{t('auth.forgot.backToLogin')}</Link></p>
          </form>
        )}
      </div>
    </div>
  )
}
