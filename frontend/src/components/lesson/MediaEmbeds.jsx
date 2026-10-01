import { useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { Video, FileIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { trackFileVideo, trackVimeo, trackYouTube } from '../../lib/tracking/videoPlayers'
import './MediaEmbeds.css'

// eslint-disable-next-line react-refresh/only-export-components
export function toVideoEmbedUrl(url) {
  if (!url) return null
  const yt = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`
  const vimeo = url.match(/vimeo\.com\/(\d+)/)
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`
  return null
}

const FILE_VIDEO = /\.(mp4|webm|ogg)(\?.*)?$/i
const PLAYER_TRACKERS = { file: trackFileVideo, youtube: trackYouTube, vimeo: trackVimeo }

function videoKind(url, embedUrl) {
  if (embedUrl) return embedUrl.includes('youtube.com') ? 'youtube' : 'vimeo'
  return url && FILE_VIDEO.test(url) ? 'file' : null
}

VideoEmbed.propTypes = { url: PropTypes.string, onPlayerEvent: PropTypes.func }

export function VideoEmbed({ url, onPlayerEvent }) {
  const { t } = useTranslation()
  const playerRef = useRef(null)
  const embedUrl = toVideoEmbedUrl(url)
  const kind = videoKind(url, embedUrl)

  // Report playback when the page tracks it (learner activity page only).
  useEffect(() => {
    if (!onPlayerEvent || !kind || !playerRef.current) return undefined
    return PLAYER_TRACKERS[kind](playerRef.current, onPlayerEvent)
  }, [kind, embedUrl, url, onPlayerEvent])

  if (embedUrl) {
    // The YouTube player API only talks to iframes loaded with enablejsapi=1.
    const src = onPlayerEvent && kind === 'youtube'
      ? `${embedUrl}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}`
      : embedUrl
    return (
      <div className="media-video-wrap">
        <iframe
          ref={playerRef}
          src={src}
          title={t('media.videoLessonTitle')}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    )
  }
  if (kind === 'file') {
    return <video ref={playerRef} className="media-video-file" src={url} controls />
  }
  return (
    <div className="media-placeholder">
      <Video size={48} className="media-placeholder-icon" />
      <p className="media-placeholder-label">{t('media.videoPlayer')}</p>
      {url && <a href={url} target="_blank" rel="noreferrer" className="media-open-link">{t('media.openVideo')}</a>}
    </div>
  )
}

PdfEmbed.propTypes = { url: PropTypes.string, onOpen: PropTypes.func, onDownload: PropTypes.func }

export function PdfEmbed({ url, onOpen, onDownload }) {
  const { t } = useTranslation()
  if (!url) {
    return (
      <div className="media-placeholder">
        <FileIcon size={48} className="media-placeholder-icon" />
        <p className="media-placeholder-label">{t('media.pdfDocument')}</p>
      </div>
    )
  }
  return (
    <div className="media-pdf-wrap">
      <iframe src={url} title={t('media.pdfLessonTitle')} />
      <div className="media-pdf-links">
        <a href={url} target="_blank" rel="noreferrer" className="media-open-link media-pdf-fallback" onClick={onOpen}>
          {t('media.openInNewTab')}
        </a>
        <a href={url} download className="media-open-link" onClick={onDownload}>
          {t('media.download')}
        </a>
      </div>
    </div>
  )
}
