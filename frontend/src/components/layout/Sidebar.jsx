import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map, Shield, ClipboardCheck, FileText, MessageCircle } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useMessages } from '../../context/MessagesContext'
import { MESSAGING_ENABLED } from '../../config'
import client from '../../api/client'
import './Sidebar.css'

// Grouped by what the user is doing. Everyone learns; creators, AIDEA partners
// and admins also create; admins also manage. Personal and help items sit at
// the bottom for everyone.
const LEARN = [
  { to: '/',         labelKey: 'nav.home',       Icon: House },
  { to: '/courses',  labelKey: 'nav.courses',    Icon: BookOpen },
  { to: '/learning', labelKey: 'nav.myLearning', Icon: GraduationCap },
  { to: '/pathway',  labelKey: 'nav.myPathway',  Icon: Map },
]
const CREATE = [
  { to: '/authoring', labelKey: 'nav.authoring', Icon: PenLine },
  { to: '/reviews',   labelKey: 'nav.reviews',   Icon: ClipboardCheck, badgeKey: 'reviews' },
  { to: '/analytics', labelKey: 'nav.analytics', Icon: BarChart2 },
]
const MANAGE = [
  { to: '/admin/users', labelKey: 'nav.admin', Icon: Shield },
]
const BOTTOM = [
  { to: '/messages',      labelKey: 'nav.messages',      Icon: MessageCircle, badgeKey: 'messages' },
  { to: '/documentation', labelKey: 'nav.documentation', Icon: FileText },
  { to: '/profile',       labelKey: 'nav.profile',       Icon: User },
]

const CREATOR_ROLES = ['content_creator', 'aidea_partner', 'admin']

function badgeText(count) {
  return count > 99 ? '99+' : String(count)
}

NavItems.propTypes = {
  items: PropTypes.array.isRequired,
  badges: PropTypes.object.isRequired,
  onNavigate: PropTypes.func,
  className: PropTypes.string,
}
function NavItems({ items, badges, onNavigate, className }) {
  const { t } = useTranslation()
  return (
    <ul className={className}>
      {items.map(({ to, labelKey, Icon: NavIcon, badgeKey }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={to === '/'}
            onClick={onNavigate}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            <NavIcon size={18} className="nav-icon" />
            <span>{t(labelKey)}</span>
            {badgeKey && badges[badgeKey] > 0 && (
              <span className="nav-badge" aria-label={t('nav.pendingCount', { count: badges[badgeKey] })}>
                {badgeText(badges[badgeKey])}
              </span>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

export default function Sidebar({ open = false, onNavigate }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { pathname } = useLocation()
  const { unreadCount = 0 } = useMessages() ?? {}
  const [pendingReviews, setPendingReviews] = useState(0)

  const userType = user?.profile?.user_type
  const canCreate = CREATOR_ROLES.includes(userType)
  const isAdmin = userType === 'admin'

  // Submissions awaiting this reviewer; refreshed on navigation so the badge
  // drops as soon as reviews are done.
  useEffect(() => {
    if (!canCreate) return
    let cancelled = false
    client.get('/reviews/count/')
      .then((res) => { if (!cancelled) setPendingReviews(res.data.pending ?? 0) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [canCreate, pathname])

  const sections = [
    { key: 'learn', items: LEARN },
    canCreate && { key: 'create', items: CREATE },
    isAdmin && { key: 'manage', items: MANAGE },
  ].filter(Boolean)
  // A single section needs no heading (teachers).
  const showLabels = sections.length > 1
  const bottom = MESSAGING_ENABLED ? BOTTOM : BOTTOM.filter((item) => item.to !== '/messages')
  const badges = { messages: unreadCount, reviews: canCreate ? pendingReviews : 0 }

  return (
    <aside className={`sidebar${open ? ' sidebar--open' : ''}`}>
      <div className="sidebar-logo">
        <img src="/images/logos/aidea-logo.png" alt="AIDEA" />
      </div>
      <nav className="sidebar-nav">
        {sections.map(({ key, items }) => (
          <div key={key} className="nav-section">
            {showLabels && <p className="nav-section-label">{t(`nav.sections.${key}`)}</p>}
            <NavItems items={items} badges={badges} onNavigate={onNavigate} />
          </div>
        ))}
        <NavItems items={bottom} badges={badges} onNavigate={onNavigate} className="nav-bottom" />
      </nav>
    </aside>
  )
}

Sidebar.propTypes = {
  open: PropTypes.bool,
  onNavigate: PropTypes.func,
}
