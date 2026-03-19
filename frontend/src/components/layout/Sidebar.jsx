import { NavLink } from 'react-router-dom'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine } from 'lucide-react'
import './Sidebar.css'

const NAV_ITEMS = [
  { to: '/',          label: 'Home',              Icon: House },
  { to: '/courses',   label: 'Courses',           Icon: BookOpen },
  { to: '/learning',  label: 'My Learning',       Icon: GraduationCap },
  { to: '/analytics', label: 'Content Analytics', Icon: BarChart2 },
  { to: '/profile',   label: 'Profile',           Icon: User },
  { to: '/authoring', label: 'Authoring',         Icon: PenLine },
]

export default function Sidebar() {
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
            {NAV_ITEMS.map(({ to, label, Icon: NavIcon }) => (
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
