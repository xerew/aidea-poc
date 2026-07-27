import PropTypes from 'prop-types'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Paperclip, Link2, X, Image, FileIcon, Send, CheckCircle2 } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './FeedbackWidget.css'

const CATEGORIES = ['bug', 'suggestion', 'feedback', 'feature_request', 'content_issue']
const ATTACHMENT_ICONS = { image: Image, file: FileIcon, link: Link2 }

function StatusBadge({ status, label }) {
  return <span className={`fb-status fb-status--${status}`}>{label}</span>
}

StatusBadge.propTypes = { status: PropTypes.string.isRequired, label: PropTypes.string.isRequired }

// ── Partner-only: read-only list of the caller's own submissions ──────────────
function MyFeedbackList() {
  const { t } = useTranslation()
  const [items, setItems] = useState(null)

  useEffect(() => {
    client.get('/feedback/mine/').then(res => setItems(res.data)).catch(() => setItems([]))
  }, [])

  if (!items || items.length === 0) return null
  return (
    <div className="fb-mine">
      <h3 className="fb-mine-title">{t('feedback.yourSubmissions')}</h3>
      <ul className="fb-mine-list">
        {items.map(it => (
          <li key={it.id} className="fb-mine-item">
            <span className="fb-mine-cat">{it.category_label}</span>
            <span className="fb-mine-msg">{it.message}</span>
            <StatusBadge status={it.status} label={it.status_label} />
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function FeedbackWidget() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isPartner = user?.profile?.user_type === 'aidea_partner'

  const [category, setCategory] = useState('bug')
  const [message, setMessage] = useState('')
  const [attachments, setAttachments] = useState([])
  const [linkUrl, setLinkUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const fileRef = useRef(null)

  const handleFiles = useCallback(async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (!files.length) return
    setUploading(true)
    setError('')
    try {
      for (const file of files) {
        const form = new FormData()
        form.append('file', file)
        const { data } = await client.post('/feedback/upload/', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        setAttachments(prev => [...prev, data])
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? t('feedback.uploadFailed'))
    } finally {
      setUploading(false)
    }
  }, [t])

  const addLink = () => {
    const url = linkUrl.trim()
    if (!url) return
    setAttachments(prev => [...prev, { type: 'link', url, name: url }])
    setLinkUrl('')
  }

  const removeAttachment = (idx) => setAttachments(prev => prev.filter((_, i) => i !== idx))

  const submit = async () => {
    if (!message.trim()) { setError(t('feedback.messageRequired')); return }
    setSubmitting(true)
    setError('')
    try {
      await client.post('/feedback/', { category, message: message.trim(), attachments })
      setDone(true)
      setMessage('')
      setAttachments([])
      setCategory('bug')
      setReloadKey(k => k + 1)
      setTimeout(() => setDone(false), 5000)
    } catch (err) {
      setError(err.response?.data?.detail ?? t('feedback.submitFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  const busy = submitting || uploading

  return (
    <section className="fb-card">
      <h2 className="fb-heading">{t('feedback.title')}</h2>
      <p className="fb-sub">{t('feedback.subtitle')}</p>

      <label className="fb-label">{t('feedback.categoryLabel')}</label>
      <div className="fb-cats">
        {CATEGORIES.map(c => (
          <button
            key={c}
            type="button"
            className={`fb-cat${category === c ? ' fb-cat--active' : ''}`}
            onClick={() => setCategory(c)}
          >
            {t(`feedback.categories.${c}`)}
          </button>
        ))}
      </div>

      <label className="fb-label" htmlFor="fb-message">{t('feedback.messageLabel')}</label>
      <textarea
        id="fb-message"
        className="fb-textarea"
        rows={4}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder={t('feedback.messagePlaceholder')}
      />

      {attachments.length > 0 && (
        <ul className="fb-attach-list">
          {attachments.map((att, idx) => {
            const Icon = ATTACHMENT_ICONS[att.type] ?? FileIcon
            return (
              <li key={`${att.url}-${idx}`} className="fb-attach-item">
                <Icon size={15} className="fb-attach-icon" />
                <a href={att.url} target="_blank" rel="noreferrer" className="fb-attach-name">{att.name || att.url}</a>
                <button type="button" className="fb-attach-remove" onClick={() => removeAttachment(idx)} aria-label={t('feedback.removeAttachment')}>
                  <X size={14} />
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <div className="fb-attach-controls">
        <button type="button" className="fb-attach-btn" onClick={() => fileRef.current?.click()} disabled={busy}>
          <Paperclip size={15} /> {uploading ? t('feedback.uploading') : t('feedback.addFile')}
        </button>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt"
          className="fb-file-input"
          onChange={handleFiles}
        />
        <div className="fb-link-row">
          <Link2 size={15} className="fb-link-icon" />
          <input
            type="url"
            className="fb-link-input"
            placeholder={t('feedback.linkPlaceholder')}
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addLink() } }}
          />
          <button type="button" className="fb-attach-btn" onClick={addLink} disabled={!linkUrl.trim()}>
            {t('feedback.addLink')}
          </button>
        </div>
      </div>

      {error && <p className="fb-error">{error}</p>}
      {done && <p className="fb-success"><CheckCircle2 size={16} /> {t('feedback.thanks')}</p>}

      <button type="button" className="fb-submit" onClick={submit} disabled={busy || !message.trim()}>
        <Send size={16} /> {submitting ? t('feedback.submitting') : t('feedback.submit')}
      </button>

      {isPartner && <MyFeedbackList key={reloadKey} />}
    </section>
  )
}
