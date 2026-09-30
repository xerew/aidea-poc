import PropTypes from 'prop-types'
import { TYPE_ICONS } from './resourceMeta'

TypeIcon.propTypes = { type: PropTypes.string, size: PropTypes.number }
export default function TypeIcon({ type, size = 16 }) {
  const Icon = TYPE_ICONS[type] ?? TYPE_ICONS.text
  return <Icon size={size} />
}
