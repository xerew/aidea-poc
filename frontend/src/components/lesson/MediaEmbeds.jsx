import PropTypes from 'prop-types'
import { Video, FileIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
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

VideoEmbed.propTypes = { url: PropTypes.string }

export function VideoEmbed({ url }) {
  const { t } = useTranslation()
  const embedUrl = toVideoEmbedUrl(url)
  if (embedUrl) {
    return (
      <div className="media-video-wrap">
        <iframe
          src={embedUrl}
          title={t('media.videoLessonTitle')}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    )
  }
  if (url && FILE_VIDEO.test(url)) {
    return <video className="media-video-file" src={url} controls />
  }
  return (
    <div className="media-placeholder">
      <Video size={48} className="media-placeholder-icon" />
      <p className="media-placeholder-label">{t('media.videoPlayer')}</p>
      {url && <a href={url} target="_blank" rel="noreferrer" className="media-open-link">{t('media.openVideo')}</a>}
    </div>
  )
}

PdfEmbed.propTypes = { url: PropTypes.string }

export function PdfEmbed({ url }) {
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
      <a href={url} target="_blank" rel="noreferrer" className="media-open-link media-pdf-fallback">
        {t('media.openInNewTab')}
      </a>
    </div>
  )
}
