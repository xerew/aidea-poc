import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import LanguageSwitcher from '../LanguageSwitcher'
import './Header.css'

export default function Header() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const initials = user?.profile?.avatar_initials ||
    `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase()

  return (
    <header className="header">
      <div className="header-title">{t('header.platform')}</div>

      <div className="header-search">
        <Search size={15} className="search-icon" />
        <input type="text" placeholder={t('common.search')} />
      </div>

      <LanguageSwitcher />

      <div className="header-user" onClick={() => setMenuOpen((o) => !o)}>
        <div className="avatar">{initials}</div>
        <span className="username">
          {user?.first_name} {user?.last_name}
        </span>
        <ChevronDown size={15} className="chevron" />

        {menuOpen && (
          <div className="user-menu">
            <button onClick={logout}>{t('common.signOut')}</button>
          </div>
        )}
      </div>
    </header>
  )
}
