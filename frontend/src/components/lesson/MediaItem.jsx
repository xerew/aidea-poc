import PropTypes from 'prop-types'
import { VideoEmbed, PdfEmbed } from './MediaEmbeds'
import './MediaItem.css'

/** Renders one media attachment (image / video / pdf) with an optional caption.
 *  Shared by the authoring preview and the learner lesson view. */
export default function MediaItem({ item, tracking }) {
  const { type, url, caption } = item
  if (!url) return null
  const image = <img src={url} alt={caption || ''} className="media-item-image" />
  return (
    <figure className="media-item-view">
      {type === 'video' && <VideoEmbed url={url} onPlayerEvent={tracking?.onPlayerEvent} />}
      {type === 'pdf' && <PdfEmbed url={url} onOpen={tracking?.onPdfOpen} onDownload={tracking?.onPdfDownload} />}
      {type === 'image' && (tracking
        ? <a href={url} target="_blank" rel="noreferrer" onClick={tracking.onImageOpen}>{image}</a>
        : image)}
      {caption && <figcaption className="media-item-caption-text">{caption}</figcaption>}
    </figure>
  )
}

MediaItem.propTypes = {
  item: PropTypes.shape({
    type: PropTypes.string,
    url: PropTypes.string,
    caption: PropTypes.string,
  }).isRequired,
  // Learner page only: report video playback, PDF open/download, image open.
  tracking: PropTypes.shape({
    onPlayerEvent: PropTypes.func,
    onPdfOpen: PropTypes.func,
    onPdfDownload: PropTypes.func,
    onImageOpen: PropTypes.func,
  }),
}
