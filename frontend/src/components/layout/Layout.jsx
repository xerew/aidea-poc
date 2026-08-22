import { useEffect, useState } from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangle } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import client from '../../api/client'
import { AccessRequestProvider, useAccessRequest } from '../../context/AccessRequestContext'
import { MessagesProvider } from '../../context/MessagesContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Footer from './Footer'
import StudyGate from '../StudyGate'
import './Layout.css'

function DenialBanner() {
  const { t } = useTranslation()
  const { request, dismiss } = useAccessRequest()
  if (!request || request.status !== 'denied' || request.denial_seen) return null
  return (
    <div className="denial-banner">
      <span>{t('layout.denialBanner', { reason: request.denial_reason })}</span>
      <button
        className="denial-banner-close"
        onClick={() => dismiss(request.id)}
        aria-label={t('common.dismiss')}
      >
        ×
      </button>
    </div>
  )
}

function MaintenanceBanner() {
  const { t, i18n } = useTranslation()
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await client.get('/maintenance/')
        if (!cancelled && res.data.active) setNotice(res.data)
      } catch { /* ignore */ }
    })()
    return () => { cancelled = true }
  }, [])

  if (!notice) return null
  const fmt = (iso) =>
    iso ? new Date(iso).toLocaleString(i18n.language, { dateStyle: 'medium', timeStyle: 'short' }) : ''
  const hasWindow = notice.starts_at && notice.ends_at

  return (
    <div className="maintenance-banner">
      <AlertTriangle size={16} className="maintenance-banner-icon" />
      <span>
        {hasWindow
          ? t('layout.maintenanceBanner', { start: fmt(notice.starts_at), end: fmt(notice.ends_at) })
          : t('layout.maintenanceBannerGeneric')}
        {notice.message ? ` ${notice.message}` : ''}
      </span>
    </div>
  )
}

function VerifyEmailBanner() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [state, setState] = useState('idle') // idle | sending | sent | error
  // Only nudge accounts explicitly flagged unverified (grandfathered/older
  // cached sessions without the field don't trigger it).
  if (user?.profile?.email_verified !== false) return null

  const resend = async () => {
    setState('sending')
    try {
      await client.post('/auth/verify-email/resend/')
      setState('sent')
    } catch {
      setState('error')
    }
  }

  return (
    <div className="verify-banner">
      <span>{t('layout.verifyBanner')}</span>
      {state === 'sent' ? (
        <span className="verify-banner-sent">{t('layout.verifyResent')}</span>
      ) : (
        <button className="verify-banner-btn" onClick={resend} disabled={state === 'sending'}>
          {state === 'sending' ? t('common.loading') : t('layout.verifyResend')}
        </button>
      )}
    </div>
  )
}

function LayoutInner() {
  const { user } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const closeDrawer = () => setDrawerOpen(false)

  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="layout">
      <Sidebar open={drawerOpen} onNavigate={closeDrawer} />
      {drawerOpen && (
        <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} />
      )}
      <div className="layout-body">
        <Header onMenuClick={() => setDrawerOpen((o) => !o)} />
        <MaintenanceBanner />
        <StudyGate />
        <VerifyEmailBanner />
        <DenialBanner />
        <main className="layout-main">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}

export default function Layout() {
  return (
    <AccessRequestProvider>
      <MessagesProvider>
        <LayoutInner />
      </MessagesProvider>
    </AccessRequestProvider>
  )
}
