import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Brain, Wrench, Compass, ExternalLink, Download, FileText, Languages } from 'lucide-react'
import FeedbackWidget from '../components/FeedbackWidget'
import './DocumentationPage.css'

// Languages the guide PDF is built in (docs/build_user_guide_pdf.py), with their
// native names. Falls back to English for anything not listed here.
const GUIDE_LANGS = [
  { code: 'en', name: 'English' },
  { code: 'el', name: 'Ελληνικά' },
  { code: 'fr', name: 'Français' },
  { code: 'es', name: 'Español' },
  { code: 'it', name: 'Italiano' },
  { code: 'fi', name: 'Suomi' },
  { code: 'sv', name: 'Svenska' },
  { code: 'no', name: 'Norsk' },
  { code: 'de', name: 'Deutsch' },
]

const guidePdf = (lang) => `/aidea-user-guide.${lang}.pdf`

const PILLARS = [
  { key: 'about', Icon: Brain },
  { key: 'with',  Icon: Wrench },
  { key: 'for',   Icon: Compass },
]

export default function DocumentationPage() {
  const { t, i18n } = useTranslation()

  const uiLang = i18n.language?.split('-')[0]
  const initial = GUIDE_LANGS.some(l => l.code === uiLang) ? uiLang : 'en'
  const [lang, setLang] = useState(initial)
  const pdf = guidePdf(lang)

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
            <label className="doc-lang">
              <Languages size={16} />
              <span className="doc-lang-label">{t('documentation.guideLanguage')}</span>
              <select
                className="doc-lang-select"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                aria-label={t('documentation.guideLanguage')}
              >
                {GUIDE_LANGS.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
            </label>
            <a className="doc-btn doc-btn--primary" href={pdf} target="_blank" rel="noreferrer">
              <ExternalLink size={16} /> {t('documentation.openGuide')}
            </a>
            <a className="doc-btn" href={pdf} download>
              <Download size={16} /> {t('documentation.downloadGuide')}
            </a>
          </div>
        </div>

        <object className="doc-pdf" data={pdf} type="application/pdf" aria-label={t('documentation.guideTitle')}>
          <p className="doc-pdf-fallback">
            {t('documentation.pdfFallback')}{' '}
            <a href={pdf} target="_blank" rel="noreferrer">{t('documentation.openGuide')}</a>
          </p>
        </object>
      </section>

      {/* Feedback */}
      <FeedbackWidget />
    </div>
  )
}
