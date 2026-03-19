import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'
import './Layout.css'

export default function Layout() {
  const { user } = useAuth()

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-body">
        <Header />
        <main className="layout-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
