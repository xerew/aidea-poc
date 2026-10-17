import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Loader2, Sparkles } from 'lucide-react'
import CriteriaList from './CriteriaList'
import { percent, verdictTone } from './aiReview'
import './AIReview.css'

/** Reviewer's view of the AI pre-check: verdict, criteria, duplicate flags, notes. */
export default function AIReviewBox({ review, onUseFeedback }) {
  const { t } = useTranslation()
  if (review.status === 'queued' || review.status === 'running') {
    return <p className="rv-ai rv-ai--pending"><Loader2 size={14} /> {t('reviews.ai.running')}</p>
  }
  if (review.status !== 'done') return null
  return (
    <div className={`rv-ai rv-ai--${verdictTone(review.verdict)}`}>
      <div className="rv-ai-head">
        <span className="rv-ai-title"><Sparkles size={15} /> {t('reviews.ai.title')}</span>
        <span className="rv-ai-verdict">{t(`reviews.ai.verdict.${review.verdict}`)}</span>
        {review.confidence != null && (
          <span className="rv-ai-conf">{t('reviews.ai.confidence', { pct: percent(review.confidence) })}</span>
        )}
        {review.spot_check && <span className="rv-ai-tag">{t('reviews.ai.spotCheck')}</span>}
      </div>
      {(review.duplicates ?? []).map((d, i) => (
        <p key={i} className="rv-ai-flag">
          <AlertTriangle size={14} />
          {t('reviews.ai.duplicate', { learner: d.learner, match: t(`reviews.ai.match.${d.match}`) })}
        </p>
      ))}
      <CriteriaList criteria={review.criteria ?? []} />
      {review.reviewer_notes && (
        <p className="rv-ai-notes"><strong>{t('reviews.ai.notes')}</strong> {review.reviewer_notes}</p>
      )}
      {review.learner_feedback && onUseFeedback && (
        <button type="button" className="rv-btn rv-ai-use" onClick={() => onUseFeedback(review.learner_feedback)}>
          {t('reviews.ai.useFeedback')}
        </button>
      )}
    </div>
  )
}

AIReviewBox.propTypes = {
  review: PropTypes.shape({
    status: PropTypes.string.isRequired,
    verdict: PropTypes.string,
    confidence: PropTypes.number,
    criteria: PropTypes.array,
    duplicates: PropTypes.array,
    reviewer_notes: PropTypes.string,
    learner_feedback: PropTypes.string,
    spot_check: PropTypes.bool,
  }).isRequired,
  onUseFeedback: PropTypes.func,
}
