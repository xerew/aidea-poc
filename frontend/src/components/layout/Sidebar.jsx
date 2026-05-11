import { NavLink } from 'react-router-dom'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map } from 'lucide-react'
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

const AUTHORING_ITEM = { to: '/authoring', label: 'Authoring', Icon: PenLine }

export default function Sidebar() {
  const { user } = useAuth()
  const isContentCreator = user?.profile?.user_type === 'content_creator'
  const navItems = isContentCreator
    ? [...BASE_NAV.filter(item => item.to !== '/pathway'), AUTHORING_ITEM]
    : BASE_NAV

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img
          src="https://aideaacademy.eu/demo/wp-content/uploads/2026/01/aidea-logo-3-AIdEA-COLORED-162px.png"
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
