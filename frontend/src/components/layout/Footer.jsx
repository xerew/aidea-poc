import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import './Footer.css'

export default function Footer() {
  const { t } = useTranslation()

  return (
    <footer className="footer">
      <div className="footer-eu">
        <img
          src="/images/logos/eu-cofunded.webp"
          alt="Co-funded by the European Union"
          className="footer-eu-logo"
        />
        <p className="footer-eu-text">
          {t('footer.funded')}
        </p>
      </div>
      <div className="footer-bottom">
        <span>
          © {new Date().getFullYear()} AIDEA by ICCS —{' '}
          <a href="https://imu.ntua.gr/wp/" target="_blank" rel="noopener noreferrer">
            Information Management Unit
          </a>
        </span>
        <div className="footer-links">
          <Link to="/terms">{t('legal.termsTitle')}</Link>
          <Link to="/privacy">{t('legal.privacyTitle')}</Link>
          <a href="https://aideaacademy.eu/" target="_blank" rel="noopener noreferrer">
            aideaacademy.eu
          </a>
        </div>
      </div>
    </footer>
  )
}
