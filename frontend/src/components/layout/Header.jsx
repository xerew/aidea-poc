import { useState } from 'react'
import { Search, ChevronDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './Header.css'

export default function Header() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const initials = user?.profile?.avatar_initials ||
    `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase()

  return (
    <header className="header">
      <div className="header-title">AI Teacher Training Platform</div>

      <div className="header-search">
        <Search size={15} className="search-icon" />
        <input type="text" placeholder="Search courses..." />
      </div>

      <div className="header-user" onClick={() => setMenuOpen((o) => !o)}>
        <div className="avatar">{initials}</div>
        <span className="username">
          {user?.first_name} {user?.last_name}
        </span>
        <ChevronDown size={15} className="chevron" />

        {menuOpen && (
          <div className="user-menu">
            <button onClick={logout}>Sign out</button>
          </div>
        )}
      </div>
    </header>
  )
}
