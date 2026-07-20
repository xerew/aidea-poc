import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import el from './locales/el.json'
import fr from './locales/fr.json'
import es from './locales/es.json'
import it from './locales/it.json'
import fi from './locales/fi.json'
import sv from './locales/sv.json'
import no from './locales/no.json'
import de from './locales/de.json'

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'el', label: 'Ελληνικά' },
  { code: 'fr', label: 'Français' },
  { code: 'es', label: 'Español' },
  { code: 'it', label: 'Italiano' },
  { code: 'fi', label: 'Suomi' },
  { code: 'sv', label: 'Svenska' },
  { code: 'no', label: 'Norsk' },
  { code: 'de', label: 'Deutsch' },
]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en }, el: { translation: el }, fr: { translation: fr },
      es: { translation: es }, it: { translation: it }, fi: { translation: fi },
      sv: { translation: sv }, no: { translation: no }, de: { translation: de },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'el', 'fr', 'es', 'it', 'fi', 'sv', 'no', 'de'],
    detection: { order: ['localStorage', 'navigator'], lookupLocalStorage: 'aidea_lang', caches: ['localStorage'] },
    interpolation: { escapeValue: false },
  })

export default i18n
