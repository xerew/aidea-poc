import PropTypes from 'prop-types'
import { VideoEmbed, PdfEmbed } from './MediaEmbeds'
import './MediaItem.css'

/** Renders one media attachment (image / video / pdf) with an optional caption.
 *  Shared by the authoring preview and the learner lesson view. */
export default function MediaItem({ item }) {
  const { type, url, caption } = item
  if (!url) return null
  return (
    <figure className="media-item-view">
      {type === 'video' && <VideoEmbed url={url} />}
      {type === 'pdf' && <PdfEmbed url={url} />}
      {type === 'image' && <img src={url} alt={caption || ''} className="media-item-image" />}
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
}
