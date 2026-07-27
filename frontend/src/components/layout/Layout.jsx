import { useState } from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../context/AuthContext'
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
