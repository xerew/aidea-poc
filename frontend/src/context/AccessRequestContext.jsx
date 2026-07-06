import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useAuth } from './AuthContext'
import client from '../api/client'

const AccessRequestContext = createContext(null)

export function AccessRequestProvider({ children }) {
  const { user } = useAuth()
  const [request, setRequest] = useState(null)
  const [loading, setLoading] = useState(false)

  const refetch = useCallback(async () => {
    if (!user) { setRequest(null); return }
    setLoading(true)
    try {
      const { data } = await client.get('/access-requests/mine/')
      setRequest(data)
    } catch {
      setRequest(null)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { refetch() }, [refetch])

  const submit = useCallback(async (message) => {
    const { data } = await client.post('/access-requests/', { message })
    setRequest(data)
    return data
  }, [])

  const cancel = useCallback(async (id) => {
    await client.delete(`/access-requests/${id}/`)
    setRequest(null)
  }, [])

  const dismiss = useCallback(async (id) => {
    await client.patch(`/access-requests/${id}/seen/`)
    setRequest(prev => prev ? { ...prev, denial_seen: true } : prev)
  }, [])

  return (
    <AccessRequestContext.Provider value={{ request, loading, submit, cancel, dismiss, refetch }}>
      {children}
    </AccessRequestContext.Provider>
  )
}

AccessRequestProvider.propTypes = { children: PropTypes.node.isRequired }

// eslint-disable-next-line react-refresh/only-export-components
export function useAccessRequest() {
  return useContext(AccessRequestContext)
}
