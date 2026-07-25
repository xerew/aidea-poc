import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { getAvatarSrc } from '../../lib/avatar'
import LanguageSwitcher from '../LanguageSwitcher'
import CourseSearch from './CourseSearch'
import './Header.css'

export default function Header() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const initials = user?.profile?.avatar_initials ||
    `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase()
  const avatarSrc = getAvatarSrc(user?.profile)

  return (
    <header className="header">
      <div className="header-title">{t('header.platform')}</div>

      <CourseSearch />

      <LanguageSwitcher />

      <div className="header-user" onClick={() => setMenuOpen((o) => !o)}>
        {avatarSrc
          ? <img className="avatar avatar--img" src={avatarSrc} alt={initials} />
          : <div className="avatar">{initials}</div>}
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
