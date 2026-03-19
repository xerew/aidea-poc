import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './LoginPage.css'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <img
          src="https://aideaacademy.eu/demo/wp-content/uploads/2026/01/aidea-logo-3-AIdEA-COLORED-162px.png"
          alt="AIDEA"
          className="login-logo"
        />
        <p className="login-subtitle">Teacher AI Training Platform</p>

        <form onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="login-footer">
          <img
            src="https://aideaacademy.eu/demo/wp-content/uploads/2026/03/EN-Co-funded-by-the-EU_PANTONE-300x63-1.jpg"
            alt="Co-funded by the European Union"
            className="login-eu-logo"
          />
          <p className="login-eu-text">
            Funded by the European Union. Views and opinions expressed are however those of the
            author(s) only and do not necessarily reflect those of the European Union or the EACEA.
          </p>
        </div>
      </div>
    </div>
  )
}
