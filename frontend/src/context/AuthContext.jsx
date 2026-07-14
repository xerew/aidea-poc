import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import PropTypes from 'prop-types'
import client from '../api/client'

const AuthContext = createContext(null)

AuthProvider.propTypes = { children: PropTypes.node }

const KEYS = ['access_token', 'refresh_token', 'user']

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user') || sessionStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  // Persistent login — survives tab close (localStorage)
  const login = useCallback(async (username, password) => {
    const { data } = await client.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  // Session-only login — cleared when the tab closes (sessionStorage)
  const loginSession = useCallback((data) => {
    sessionStorage.setItem('access_token', data.access)
    sessionStorage.setItem('refresh_token', data.refresh)
    sessionStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token')
    try {
      await client.post('/auth/logout/', { refresh })
    } finally {
      KEYS.forEach(k => { localStorage.removeItem(k); sessionStorage.removeItem(k) })
      setUser(null)
    }
  }, [])

  const updateUser = useCallback((updates) => {
    setUser(prev => {
      const updated = { ...prev, ...updates }
      const store = localStorage.getItem('user') ? localStorage : sessionStorage
      store.setItem('user', JSON.stringify(updated))
      return updated
    })
  }, [])

  // Refresh user data from the server on mount so server-side role changes
  // (e.g. content-creator approval) propagate without re-login.
  useEffect(() => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
    if (!token) return
    client.get('/auth/me/')
      .then(({ data }) => {
        const store = localStorage.getItem('user') ? localStorage : sessionStorage
        store.setItem('user', JSON.stringify(data))
        setUser(data)
      })
      .catch(() => {}) // interceptor handles 401 → login redirect
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, loginSession, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
