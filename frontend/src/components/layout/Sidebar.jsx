import PropTypes from 'prop-types'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map, Shield, ClipboardCheck } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

const BASE_NAV = [
  { to: '/',          labelKey: 'nav.home',       Icon: House },
  { to: '/courses',   labelKey: 'nav.courses',    Icon: BookOpen },
  { to: '/learning',  labelKey: 'nav.myLearning',  Icon: GraduationCap },
  { to: '/pathway',   labelKey: 'nav.myPathway',   Icon: Map },
  { to: '/analytics', labelKey: 'nav.analytics',   Icon: BarChart2 },
  { to: '/profile',   labelKey: 'nav.profile',     Icon: User },
]

const AUTHORING_ITEM = { to: '/authoring',    labelKey: 'nav.authoring', Icon: PenLine }
const ADMIN_ITEM     = { to: '/admin/users',  labelKey: 'nav.admin',     Icon: Shield  }
const REVIEWS_ITEM   = { to: '/reviews',      labelKey: 'nav.reviews',   Icon: ClipboardCheck }

// Content creators, AIDEA partners and admins share the content-creation nav
// (authoring + reviews). Admins additionally get the Admin dashboard.
const CREATOR_NAV = [...BASE_NAV.filter(item => item.to !== '/pathway'), REVIEWS_ITEM, AUTHORING_ITEM]

export default function Sidebar({ open = false, onNavigate }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const userType = user?.profile?.user_type

  let navItems
  if (userType === 'admin') {
    navItems = [...CREATOR_NAV, ADMIN_ITEM]
  } else if (userType === 'content_creator' || userType === 'aidea_partner') {
    navItems = CREATOR_NAV
  } else {
    navItems = BASE_NAV
  }

  return (
    <aside className={`sidebar${open ? ' sidebar--open' : ''}`}>
      <div className="sidebar-logo">
        <img
          src="/images/logos/aidea-logo.png"
          alt="AIDEA"
        />
      </div>
      <nav>
        <ul>
          {navItems.map(({ to, labelKey, Icon: NavIcon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                onClick={onNavigate}
                className={({ isActive }) => isActive ? 'active' : ''}
              >
                <NavIcon size={18} className="nav-icon" />
                <span>{t(labelKey)}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}

Sidebar.propTypes = {
  open: PropTypes.bool,
  onNavigate: PropTypes.func,
}
