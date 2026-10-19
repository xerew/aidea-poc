import { useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Maximize2 } from 'lucide-react'
import { API_BASE } from '../../api/client'
import { absoluteUrl, isPrivateHost, officeViewerUrl } from '../../lib/presentation'
import { watchFrameFocus } from '../../lib/tracking/frameFocus'
import './PresentationFrame.css'

/** A .pptx played by Microsoft's Office viewer (16:9), or — on development
 *  hosts Microsoft cannot reach — a notice. */
export default function PresentationFrame({ url, title, onFocusChange }) {
  const { t } = useTranslation()
  const frameRef = useRef(null)
  const fileUrl = absoluteUrl(url, API_BASE)
  const local = isPrivateHost(fileUrl)

  useEffect(() => {
    if (local || !onFocusChange || !frameRef.current) return undefined
    return watchFrameFocus(frameRef.current, onFocusChange)
  }, [local, onFocusChange])

  if (local) {
    return <p className="pres-notice">{t('lesson.presentation.livePreviewOnly')}</p>
  }
  return (
    <div className="pres-frame">
      <div className="pres-wrap">
        <iframe ref={frameRef} src={officeViewerUrl(fileUrl)} title={t('lesson.presentation.frameTitle', { title })}
          allowFullScreen />
      </div>
      <button type="button" className="pres-fullscreen" onClick={() => frameRef.current?.requestFullscreen?.()}>
        <Maximize2 size={14} /> {t('lesson.presentation.fullscreen')}
      </button>
    </div>
  )
}

PresentationFrame.propTypes = {
  url: PropTypes.string.isRequired,
  title: PropTypes.string,
  onFocusChange: PropTypes.func,
}
