import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, X } from 'lucide-react'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { PasswordInput, PasswordStrengthPanel, PASSWORD_RULES } from '../components/PasswordInput'
import client from '../api/client'
import './LoginPage.css'

export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const { uid, token } = useParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  const allRulesMet = PASSWORD_RULES.every(r => r.test(password))
  const passwordsMatch = password.length > 0 && password === confirm

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!allRulesMet) { setError(t('auth.reset.rulesNotMet')); return }
    if (!passwordsMatch) { setError(t('auth.reset.noMatch')); return }
    setLoading(true)
    try {
      await client.post('/auth/password-reset/confirm/', { uid, token, new_password: password })
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setError(err?.response?.data?.detail || t('auth.reset.failed'))
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
        <img src="/images/logos/aidea-logo.png" alt="AIDEA" className="login-logo" />
        <p className="login-subtitle">{t('auth.reset.subtitle')}</p>

        {done ? (
          <>
            <p className="login-info">{t('auth.reset.success')}</p>
            <p className="login-signup-link"><Link to="/login">{t('auth.reset.goToLogin')}</Link></p>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && <div className="login-error">{error}</div>}
            <div className="field">
              <label htmlFor="new-password">{t('auth.reset.newPassword')}</label>
              <PasswordInput
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.reset.newPasswordPlaceholder')}
                autoComplete="new-password"
              />
              <PasswordStrengthPanel password={password} />
            </div>
            <div className="field">
              <label htmlFor="confirm-password">{t('auth.reset.confirmPassword')}</label>
              <PasswordInput
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder={t('auth.reset.confirmPlaceholder')}
                autoComplete="new-password"
              />
              {confirm && (
                <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                  {passwordsMatch
                    ? <><Check size={12} /> {t('auth.password.match')}</>
                    : <><X size={12} /> {t('auth.password.noMatch')}</>}
                </span>
              )}
            </div>
            <button type="submit" disabled={loading || !allRulesMet || !passwordsMatch}>
              {loading ? t('auth.reset.resetting') : t('auth.reset.resetButton')}
            </button>
            <p className="login-signup-link"><Link to="/login">{t('auth.reset.goToLogin')}</Link></p>
          </form>
        )}
      </div>
    </div>
  )
}
