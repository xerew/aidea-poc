import { useTranslation } from 'react-i18next'
import LegalDocument from '../components/LegalDocument'
import LegalLayout from '../components/LegalLayout'

// The terms text lives in content/terms/<lang>.js (English is the reference).
const LOADERS = {
  en: () => import('../content/terms/en.js'),
  el: () => import('../content/terms/el.js'),
  fr: () => import('../content/terms/fr.js'),
  es: () => import('../content/terms/es.js'),
  it: () => import('../content/terms/it.js'),
  fi: () => import('../content/terms/fi.js'),
  sv: () => import('../content/terms/sv.js'),
  no: () => import('../content/terms/no.js'),
  de: () => import('../content/terms/de.js'),
}
const UPDATED = new Date(2026, 6, 1)   // July 2026 (the text hasn't changed since)

export default function TermsPage() {
  const { t } = useTranslation()
  return (
    <LegalLayout title={t('legal.termsTitle')} updated={UPDATED}>
      <LegalDocument loaders={LOADERS} />
    </LegalLayout>
  )
}
