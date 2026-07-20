import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { LANGUAGES } from '../i18n'
import './LanguageSwitcher.css'

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const { user, updateUser } = useAuth()

  const change = (code) => {
    i18n.changeLanguage(code)
    if (user) {
      updateUser({ profile: { ...user.profile, language: code } })
      client.patch('/profile/language/', { language: code }).catch(() => {})
    }
  }

  return (
    <label className="lang-switcher" title={t('common.language')}>
      <Globe size={15} />
      <select value={i18n.resolvedLanguage} onChange={(e) => change(e.target.value)} aria-label={t('common.language')}>
        {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
      </select>
    </label>
  )
}
