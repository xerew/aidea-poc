import { NavLink } from 'react-router-dom'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map, Shield, ClipboardCheck } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

const BASE_NAV = [
  { to: '/',          label: 'Home',              Icon: House },
  { to: '/courses',   label: 'Courses',           Icon: BookOpen },
  { to: '/learning',  label: 'My Learning',       Icon: GraduationCap },
  { to: '/pathway',   label: 'My Pathway',        Icon: Map },
  { to: '/analytics', label: 'Content Analytics', Icon: BarChart2 },
  { to: '/profile',   label: 'Profile',           Icon: User },
]

const AUTHORING_ITEM = { to: '/authoring',    label: 'Authoring', Icon: PenLine }
const ADMIN_ITEM     = { to: '/admin/users',  label: 'Admin',     Icon: Shield  }
const REVIEWS_ITEM   = { to: '/reviews',      label: 'Reviews',   Icon: ClipboardCheck }

export default function Sidebar() {
  const { user } = useAuth()
  const userType = user?.profile?.user_type

  let navItems
  if (userType === 'admin') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), REVIEWS_ITEM, ADMIN_ITEM]
  } else if (userType === 'content_creator') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), REVIEWS_ITEM, AUTHORING_ITEM]
  } else if (userType === 'aidea_partner') {
    navItems = [
      ...BASE_NAV.filter(item => ['/', '/courses'].includes(item.to)),
      REVIEWS_ITEM,
      ...BASE_NAV.filter(item => item.to === '/profile'),
    ]
  } else {
    navItems = BASE_NAV
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img
          src="/images/logos/aidea-logo.png"
          alt="AIDEA"
        />
      </div>
      <nav>
        <ul>
          {navItems.map(({ to, label, Icon: NavIcon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) => isActive ? 'active' : ''}
              >
                <NavIcon size={18} className="nav-icon" />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
