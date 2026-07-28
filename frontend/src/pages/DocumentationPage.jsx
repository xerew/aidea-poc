import { useTranslation } from 'react-i18next'
import { Brain, Wrench, Compass, ExternalLink, Download, FileText } from 'lucide-react'
import FeedbackWidget from '../components/FeedbackWidget'
import './DocumentationPage.css'

const GUIDE_PDF = '/aidea-user-guide.pdf'

const PILLARS = [
  { key: 'about', Icon: Brain },
  { key: 'with',  Icon: Wrench },
  { key: 'for',   Icon: Compass },
]

export default function DocumentationPage() {
  const { t } = useTranslation()

  return (
    <div className="doc-page">
      {/* About the project */}
      <section className="doc-hero">
        <img className="doc-logo" src="/images/logos/aidea-logo.png" alt="AIDEA" />
        <div className="doc-hero-text">
          <h1>{t('documentation.title')}</h1>
          <p className="doc-tagline">{t('documentation.tagline')}</p>
          <p className="doc-mission">{t('documentation.mission')}</p>
        </div>
      </section>

      <section className="doc-pillars">
        {PILLARS.map(({ key, Icon }) => (
          <div key={key} className="doc-pillar">
            <Icon size={22} className="doc-pillar-icon" />
            <h3>{t(`documentation.pillars.${key}.title`)}</h3>
            <p>{t(`documentation.pillars.${key}.desc`)}</p>
          </div>
        ))}
      </section>

      <p className="doc-funding">{t('documentation.funding')}</p>

      {/* User guide */}
      <section className="doc-guide">
        <div className="doc-guide-head">
          <div className="doc-guide-title">
            <FileText size={20} className="doc-guide-icon" />
            <div>
              <h2>{t('documentation.guideTitle')}</h2>
              <p>{t('documentation.guideDesc')}</p>
            </div>
          </div>
          <div className="doc-guide-actions">
            <a className="doc-btn doc-btn--primary" href={GUIDE_PDF} target="_blank" rel="noreferrer">
              <ExternalLink size={16} /> {t('documentation.openGuide')}
            </a>
            <a className="doc-btn" href={GUIDE_PDF} download>
              <Download size={16} /> {t('documentation.downloadGuide')}
            </a>
          </div>
        </div>

        <object className="doc-pdf" data={GUIDE_PDF} type="application/pdf" aria-label={t('documentation.guideTitle')}>
          <p className="doc-pdf-fallback">
            {t('documentation.pdfFallback')}{' '}
            <a href={GUIDE_PDF} target="_blank" rel="noreferrer">{t('documentation.openGuide')}</a>
          </p>
        </object>
      </section>

      {/* Feedback */}
      <FeedbackWidget />
    </div>
  )
}
