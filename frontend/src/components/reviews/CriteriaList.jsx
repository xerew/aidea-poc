import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, CircleDot, XCircle, HelpCircle } from 'lucide-react'
import { statusIcon } from './aiReview'
import './AIReview.css'

const ICONS = { check: CheckCircle2, half: CircleDot, cross: XCircle, question: HelpCircle }

/** The AI's per-criterion results: icon (met / partly / not / can't tell), name, reason. */
export default function CriteriaList({ criteria }) {
  const { t } = useTranslation()
  return (
    <ul className="air-criteria">
      {criteria.map((c, i) => {
        const kind = statusIcon(c.status)
        const Icon = ICONS[kind]
        return (
          <li key={c.id ?? i} className={`air-criterion air-criterion--${kind}`}>
            <Icon size={15} className="air-criterion-icon" aria-label={t(`reviews.ai.status.${c.status}`)} />
            <span><strong>{c.name}</strong>{c.reason ? ` — ${c.reason}` : ''}</span>
          </li>
        )
      })}
    </ul>
  )
}

CriteriaList.propTypes = {
  criteria: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    status: PropTypes.string,
    reason: PropTypes.string,
  })).isRequired,
}
