import { NavLink } from 'react-router-dom'
import './Sidebar.css'

const NAV_ITEMS = [
  { to: '/',          label: 'Home',              icon: '⌂' },
  { to: '/courses',   label: 'Courses',            icon: '📖' },
  { to: '/learning',  label: 'My Learning',        icon: '🎓' },
  { to: '/analytics', label: 'Content Analytics',  icon: '📈' },
  { to: '/profile',   label: 'Profile',            icon: '👤' },
  { to: '/authoring', label: 'Authoring',          icon: '✏️' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <nav>
        <ul>
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <li key={to}>
              <NavLink to={to} end={to === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
                <span className="nav-icon">{icon}</span>
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
