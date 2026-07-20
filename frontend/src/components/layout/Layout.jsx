import { Outlet, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../context/AuthContext'
import { AccessRequestProvider, useAccessRequest } from '../../context/AccessRequestContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Footer from './Footer'
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

function LayoutInner() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-body">
        <Header />
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
      <LayoutInner />
    </AccessRequestProvider>
  )
}
