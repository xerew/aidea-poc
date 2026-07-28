import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft } from 'lucide-react'
import './LegalLayout.css'

export default function LegalLayout({ title, children }) {
  const { t } = useTranslation()
  return (
    <div className="legal-page">
      <div className="legal-card">
        <Link to="/" className="legal-back"><ArrowLeft size={16} /> {t('common.back')}</Link>
        <img src="/images/logos/aidea-logo.png" alt="AIDEA" className="legal-logo" />
        <h1 className="legal-title">{title}</h1>
        <p className="legal-updated">{t('legal.lastUpdated', { date: 'July 2026' })}</p>
        <div className="legal-body">{children}</div>
        <div className="legal-footer">
          <Link to="/terms">{t('legal.termsTitle')}</Link>
          <span>·</span>
          <Link to="/privacy">{t('legal.privacyTitle')}</Link>
          <span>·</span>
          <a href="https://imu.ntua.gr/wp/" target="_blank" rel="noreferrer">Information Management Unit</a>
        </div>
      </div>
    </div>
  )
}

LegalLayout.propTypes = { title: PropTypes.string.isRequired, children: PropTypes.node }
