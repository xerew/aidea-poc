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
        <span>© {new Date().getFullYear()} AIDEA by ICCS</span>
        <a href="https://aideaacademy.eu/demo/" target="_blank" rel="noopener noreferrer">
          aideaacademy.eu
        </a>
      </div>
    </footer>
  )
}
