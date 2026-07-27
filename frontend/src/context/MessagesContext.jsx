import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { useAuth } from './AuthContext'
import client from '../api/client'
import { MESSAGING_ENABLED } from '../config'

const MessagesContext = createContext(null)

const POLL_MS = 30000

export function MessagesProvider({ children }) {
  const { user } = useAuth()
  const [unreadCount, setUnreadCount] = useState(0)
  const timerRef = useRef(null)

  const refreshUnread = useCallback(async () => {
    try {
      const { data } = await client.get('/messages/unread-count/')
      setUnreadCount(data.unread ?? 0)
    } catch {
      /* leave the last known count in place */
    }
  }, [])

  useEffect(() => {
    if (!user || !MESSAGING_ENABLED) return undefined
    let cancelled = false
    const tick = async () => {
      try {
        const { data } = await client.get('/messages/unread-count/')
        if (!cancelled) setUnreadCount(data.unread ?? 0)
      } catch { /* leave the last known count in place */ }
    }
    tick()
    timerRef.current = window.setInterval(tick, POLL_MS)
    return () => { cancelled = true; window.clearInterval(timerRef.current) }
  }, [user])

  return (
    <MessagesContext.Provider value={{ unreadCount, refreshUnread }}>
      {children}
    </MessagesContext.Provider>
  )
}

MessagesProvider.propTypes = { children: PropTypes.node.isRequired }

// eslint-disable-next-line react-refresh/only-export-components
export function useMessages() {
  return useContext(MessagesContext)
}
