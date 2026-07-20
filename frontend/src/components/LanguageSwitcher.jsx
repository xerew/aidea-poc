import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { LANGUAGES } from '../i18n'
import './LanguageSwitcher.css'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const { user } = useAuth()

  const change = (code) => {
    i18n.changeLanguage(code)
    if (user) client.patch('/profile/language/', { language: code }).catch(() => {})
  }

  return (
    <label className="lang-switcher" title="Language">
      <Globe size={15} />
      <select value={i18n.resolvedLanguage} onChange={(e) => change(e.target.value)} aria-label="Language">
        {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
      </select>
    </label>
  )
}
