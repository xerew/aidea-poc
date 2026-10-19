import PropTypes from 'prop-types'
import { Video, FileText, HelpCircle, Image, FileIcon, ClipboardList, Puzzle, Presentation } from 'lucide-react'

export const TYPE_ICONS = {
  video:      Video,
  text:       FileText,
  quiz:       HelpCircle,
  image:      Image,
  pdf:        FileIcon,
  assignment: ClipboardList,
  h5p:        Puzzle,
  presentation: Presentation,
}

export const resourceShape = PropTypes.shape({
  id:           PropTypes.number.isRequired,
  type:         PropTypes.string.isRequired,
  order:        PropTypes.number,
  is_required:  PropTypes.bool,
  title:        PropTypes.string,
  content:      PropTypes.string,
  url:          PropTypes.string,
  caption:      PropTypes.string,
  quiz_data:    PropTypes.array,
  instructions: PropTypes.string,
  is_completed: PropTypes.bool,
  quiz_review:  PropTypes.shape({
    selected: PropTypes.array,
    results:  PropTypes.array,
  }),
  submission:   PropTypes.object,
  h5p_self_complete: PropTypes.bool,
  presentation: PropTypes.shape({
    url:               PropTypes.string,
    title:             PropTypes.string,
    slides:            PropTypes.number,
    language:          PropTypes.string,
    size_bytes:        PropTypes.number,
    over_viewer_limit: PropTypes.bool,
    downloadable:      PropTypes.bool,
  }),
  h5p: PropTypes.shape({
    package_id:   PropTypes.number,
    path:         PropTypes.string,
    language:     PropTypes.string,
    version:      PropTypes.number,
    title:        PropTypes.string,
    main_library: PropTypes.string,
  }),
})
