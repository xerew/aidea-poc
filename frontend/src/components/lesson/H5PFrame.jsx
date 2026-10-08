import { useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { mediaUrl } from '../../lib/mediaUrl'
import './H5PFrame.css'

const LOAD_TIMEOUT_MS = 30000
// Clock reads live outside components (React compiler purity rule).
const nowMs = () => Date.now()

/** One H5P package in a sandboxed (opaque-origin) frame. The frame can run
 *  the activity's scripts but cannot read AIDEA's pages, cookies or tokens.
 *  Messages are accepted only from this frame's window and channel. */
export default function H5PFrame({ pkg, title, onStatement, onError }) {
  const { t } = useTranslation()
  const frameRef = useRef(null)
  const [height, setHeight] = useState(480)
  const [failed, setFailed] = useState(false)
  const channel = `h5p-${pkg.package_id}-${pkg.version}`
  const src = useMemo(() => {
    const params = new URLSearchParams({ src: mediaUrl(pkg.path), channel, origin: window.location.origin })
    return `/h5p/player.html?${params}`
  }, [pkg.path, channel])

  const handlersRef = useRef({ onStatement, onError })
  useEffect(() => { handlersRef.current = { onStatement, onError } })

  useEffect(() => {
    let ready = false
    const fail = (message) => {
      setFailed(true)
      handlersRef.current.onError?.(message)
    }
    const timer = setTimeout(() => { if (!ready) fail('timeout') }, LOAD_TIMEOUT_MS)
    const onMessage = (e) => {
      const msg = e.data
      if (e.source !== frameRef.current?.contentWindow || msg?.source !== 'aidea-h5p' || msg.channel !== channel) return
      if (msg.kind === 'ready') ready = true
      else if (msg.kind === 'height' && Number.isFinite(msg.height)) setHeight(Math.min(Math.max(msg.height, 200), 4000))
      else if (msg.kind === 'error') fail(String(msg.message || 'error'))
      else if (msg.kind === 'xapi') handlersRef.current.onStatement?.(msg.statement, nowMs())
    }
    window.addEventListener('message', onMessage)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('message', onMessage)
    }
  }, [channel])

  if (failed) return <p className="lp-empty">{t('lesson.h5p.loadError')}</p>
  return (
    <iframe
      ref={frameRef}
      className="h5p-frame"
      title={title}
      src={src}
      sandbox="allow-scripts allow-popups allow-forms"
      allow="fullscreen"
      style={{ height }}
    />
  )
}

H5PFrame.propTypes = {
  pkg: PropTypes.shape({
    package_id: PropTypes.number.isRequired,
    version: PropTypes.number.isRequired,
    path: PropTypes.string.isRequired,
  }).isRequired,
  title: PropTypes.string.isRequired,
  onStatement: PropTypes.func,
  onError: PropTypes.func,
}
