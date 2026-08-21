import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, XCircle } from 'lucide-react'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './LoginPage.css'

export default function VerifyEmailPage() {
  const { t } = useTranslation()
  const { token } = useParams()
  const { user, updateUser } = useAuth()
  const [status, setStatus] = useState('verifying') // verifying | success | error

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await client.post('/auth/verify-email/', { token })
        if (cancelled) return
        setStatus('success')
        // Reflect it immediately if this is the logged-in user's session.
        if (user && user.profile?.email_verified === false) {
          updateUser({ profile: { ...user.profile, email_verified: true } })
        }
      } catch {
        if (!cancelled) setStatus('error')
      }
    })()
    return () => { cancelled = true }
    // Run once for the token in the URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-lang-switcher">
          <LanguageSwitcher />
        </div>
        <img src="/images/logos/aidea-logo.png" alt="AIDEA" className="login-logo" />

        {status === 'verifying' && (
          <p className="login-info">{t('verifyEmail.verifying')}</p>
        )}

        {status === 'success' && (
          <>
            <p className="login-info" style={{ color: '#166534', display: 'flex', alignItems: 'center', gap: '0.4rem', justifyContent: 'center' }}>
              <CheckCircle2 size={18} /> {t('verifyEmail.successTitle')}
            </p>
            <p className="login-subtitle">{t('verifyEmail.successBody')}</p>
            <p className="login-signup-link">
              <Link to={user ? '/' : '/login'}>
                {user ? t('verifyEmail.goToApp') : t('verifyEmail.goToLogin')}
              </Link>
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <p className="login-error" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <XCircle size={18} /> {t('verifyEmail.errorTitle')}
            </p>
            <p className="login-subtitle">{t('verifyEmail.errorBody')}</p>
            <p className="login-signup-link">
              <Link to={user ? '/' : '/login'}>
                {user ? t('verifyEmail.goToApp') : t('verifyEmail.goToLogin')}
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
