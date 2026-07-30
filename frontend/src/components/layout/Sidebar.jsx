import PropTypes from 'prop-types'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map, Shield, ClipboardCheck, FileText, MessageCircle } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useMessages } from '../../context/MessagesContext'
import { MESSAGING_ENABLED } from '../../config'
import './Sidebar.css'

const BASE_NAV = [
  { to: '/',          labelKey: 'nav.home',       Icon: House },
  { to: '/courses',   labelKey: 'nav.courses',    Icon: BookOpen },
  { to: '/learning',  labelKey: 'nav.myLearning',  Icon: GraduationCap },
  { to: '/pathway',   labelKey: 'nav.myPathway',   Icon: Map },
  { to: '/messages',  labelKey: 'nav.messages',    Icon: MessageCircle, badgeKey: 'messages' },
  { to: '/profile',   labelKey: 'nav.profile',     Icon: User },
  { to: '/documentation', labelKey: 'nav.documentation', Icon: FileText },
]

const ANALYTICS_ITEM = { to: '/analytics',   labelKey: 'nav.analytics', Icon: BarChart2 }
const AUTHORING_ITEM = { to: '/authoring',    labelKey: 'nav.authoring', Icon: PenLine }
const ADMIN_ITEM     = { to: '/admin/users',  labelKey: 'nav.admin',     Icon: Shield  }
const REVIEWS_ITEM   = { to: '/reviews',      labelKey: 'nav.reviews',   Icon: ClipboardCheck }

// Content Analytics is a content-creation tool, so it's hidden from teachers.
// Creators, AIDEA partners and admins share the content-creation nav (analytics
// + reviews + authoring). Admins additionally get the Admin dashboard.
const CREATOR_NAV = [
  ...BASE_NAV.filter(item => item.to !== '/pathway'),
  ANALYTICS_ITEM, REVIEWS_ITEM, AUTHORING_ITEM,
]

export default function Sidebar({ open = false, onNavigate }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { unreadCount = 0 } = useMessages() ?? {}
  const userType = user?.profile?.user_type

  let navItems
  if (userType === 'admin') {
    navItems = [...CREATOR_NAV, ADMIN_ITEM]
  } else if (userType === 'content_creator' || userType === 'aidea_partner') {
    navItems = CREATOR_NAV
  } else {
    navItems = BASE_NAV
  }
  // Messaging is hidden behind a feature flag.
  if (!MESSAGING_ENABLED) navItems = navItems.filter(item => item.to !== '/messages')

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
          {navItems.map(({ to, labelKey, Icon: NavIcon, badgeKey }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                onClick={onNavigate}
                className={({ isActive }) => isActive ? 'active' : ''}
              >
                <NavIcon size={18} className="nav-icon" />
                <span>{t(labelKey)}</span>
                {badgeKey === 'messages' && unreadCount > 0 && (
                  <span className="nav-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
                )}
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
