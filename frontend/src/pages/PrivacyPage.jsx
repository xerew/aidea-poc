import { useTranslation } from 'react-i18next'
import LegalDocument from '../components/LegalDocument'
import LegalLayout from '../components/LegalLayout'

// The policy text lives in content/privacy/<lang>.js (English is the reference).
const LOADERS = {
  en: () => import('../content/privacy/en.js'),
  el: () => import('../content/privacy/el.js'),
  fr: () => import('../content/privacy/fr.js'),
  es: () => import('../content/privacy/es.js'),
  it: () => import('../content/privacy/it.js'),
  fi: () => import('../content/privacy/fi.js'),
  sv: () => import('../content/privacy/sv.js'),
  no: () => import('../content/privacy/no.js'),
  de: () => import('../content/privacy/de.js'),
}
const UPDATED = new Date(2026, 10, 1)   // November 2026: sign-in records, platform activity, Matomo user number

export default function PrivacyPage() {
  const { t } = useTranslation()
  return (
    <LegalLayout title={t('legal.privacyTitle')} updated={UPDATED}>
      <LegalDocument loaders={LOADERS} />
    </LegalLayout>
  )
}
