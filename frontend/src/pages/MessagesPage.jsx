import PropTypes from 'prop-types'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Search, Send, ArrowLeft, MessageCircle } from 'lucide-react'
import client from '../api/client'
import { getAvatarSrc } from '../lib/avatar'
import { useMessages } from '../context/MessagesContext'
import './MessagesPage.css'

function Avatar({ person, size = 40 }) {
  const src = getAvatarSrc(person)
  const style = { width: size, height: size }
  return src
    ? <img className="msg-avatar-img" style={style} src={src} alt={person.name} />
    : <div className="msg-avatar" style={style}>{person.avatar_initials || '?'}</div>
}

Avatar.propTypes = { person: PropTypes.object.isRequired, size: PropTypes.number }

function ConversationRow({ conv, active, onClick }) {
  const other = conv.other_user
  return (
    <button type="button" className={`msg-conv${active ? ' msg-conv--active' : ''}`} onClick={onClick}>
      <Avatar person={other} />
      <div className="msg-conv-text">
        <span className="msg-conv-name">{other.name}</span>
        <span className="msg-conv-preview">{conv.last_message}</span>
      </div>
      {conv.unread_count > 0 && <span className="msg-conv-badge">{conv.unread_count}</span>}
    </button>
  )
}

ConversationRow.propTypes = {
  conv: PropTypes.object.isRequired,
  active: PropTypes.bool,
  onClick: PropTypes.func.isRequired,
}

export default function MessagesPage() {
  const { t } = useTranslation()
  const { userId } = useParams()
  const navigate = useNavigate()
  const { refreshUnread } = useMessages() ?? {}

  const [conversations, setConversations] = useState([])
  const [search, setSearch] = useState('')
  const [otherUser, setOtherUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingThread, setLoadingThread] = useState(false)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef(null)

  // Reset the thread view when switching conversations (avoids setState-in-effect).
  const [loadedId, setLoadedId] = useState(userId)
  if (userId !== loadedId) {
    setLoadedId(userId)
    setMessages([])
    setOtherUser(null)
    setLoadingThread(Boolean(userId))
  }

  const loadConversations = useCallback(async () => {
    try {
      const { data } = await client.get('/messages/conversations/')
      setConversations(data)
    } catch { /* keep last list */ }
  }, [])

  useEffect(() => { loadConversations() }, [loadConversations])

  // Load the open thread and mark it read.
  useEffect(() => {
    if (!userId) return undefined
    let active = true
    client.get(`/messages/with/${userId}/`)
      .then(({ data }) => {
        if (!active) return
        setOtherUser(data.other_user)
        setMessages(data.messages)
        refreshUnread?.()
        loadConversations()
      })
      .catch(() => { if (active) setOtherUser(null) })
      .finally(() => { if (active) setLoadingThread(false) })
    return () => { active = false }
  }, [userId, refreshUnread, loadConversations])

  // Keep the newest message in view.
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'end' }) }, [messages])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return conversations
    return conversations.filter(c => c.other_user.name.toLowerCase().includes(q))
  }, [conversations, search])

  const send = async () => {
    const body = text.trim()
    if (!body || !userId) return
    setSending(true)
    try {
      const { data } = await client.post(`/messages/with/${userId}/`, { text: body })
      setMessages(prev => [...prev, data])
      setText('')
      loadConversations()
    } catch { /* ignore */ } finally {
      setSending(false)
    }
  }

  return (
    <div className={`msg-page${userId ? ' msg-page--thread-open' : ''}`}>
      {/* Conversation list */}
      <aside className="msg-list">
        <div className="msg-list-head">
          <h1 className="msg-title">{t('messages.title')}</h1>
          <div className="msg-search">
            <Search size={15} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('messages.searchPlaceholder')}
            />
          </div>
        </div>
        <div className="msg-conv-scroll">
          {filtered.length === 0 ? (
            <p className="msg-empty-list">{search ? t('messages.noMatches') : t('messages.noConversations')}</p>
          ) : (
            filtered.map(c => (
              <ConversationRow
                key={c.id}
                conv={c}
                active={String(c.other_user.id) === String(userId)}
                onClick={() => navigate(`/messages/${c.other_user.id}`)}
              />
            ))
          )}
        </div>
      </aside>

      {/* Thread */}
      <section className="msg-thread">
        {!userId ? (
          <div className="msg-thread-empty">
            <MessageCircle size={40} />
            <p>{t('messages.selectPrompt')}</p>
          </div>
        ) : (
          <>
            <header className="msg-thread-head">
              <button type="button" className="msg-back" onClick={() => navigate('/messages')} aria-label={t('common.back')}>
                <ArrowLeft size={18} />
              </button>
              {otherUser && (
                <Link to={`/users/${otherUser.id}`} className="msg-thread-person">
                  <Avatar person={otherUser} size={34} />
                  <span className="msg-thread-name">{otherUser.name}</span>
                </Link>
              )}
            </header>

            <div className="msg-scroll">
              {loadingThread ? (
                <p className="msg-thread-loading">{t('common.loading')}</p>
              ) : messages.length === 0 ? (
                <p className="msg-thread-loading">{t('messages.startPrompt')}</p>
              ) : (
                messages.map(m => (
                  <div key={m.id} className={`msg-bubble-row${m.is_mine ? ' msg-bubble-row--mine' : ''}`}>
                    <div className="msg-bubble">
                      <p className="msg-bubble-text">{m.text}</p>
                      <span className="msg-bubble-time">
                        {new Date(m.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </span>
                    </div>
                  </div>
                ))
              )}
              <div ref={endRef} />
            </div>

            <div className="msg-composer">
              <textarea
                className="msg-composer-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                placeholder={t('messages.composerPlaceholder')}
                rows={1}
              />
              <button type="button" className="msg-send" onClick={send} disabled={!text.trim() || sending}>
                <Send size={18} />
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
