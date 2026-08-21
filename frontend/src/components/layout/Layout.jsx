import { useState } from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
