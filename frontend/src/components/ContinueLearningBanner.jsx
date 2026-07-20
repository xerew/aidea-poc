import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import './ContinueLearningBanner.css'

ContinueLearningBanner.propTypes = {
  data: PropTypes.shape({
    course_id: PropTypes.number,
    course_title: PropTypes.string,
    current_module_title: PropTypes.string,
    progress_pct: PropTypes.number,
  }),
}

export default function ContinueLearningBanner({ data }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  if (!data) return null
  return (
    <div className="cl-banner">
      <p className="cl-label">{t('common.continueLearning')}</p>
      <h2 className="cl-title">{data.course_title}</h2>
      {data.current_module_title && (
        <p className="cl-next-module">{t('common.nextLabel', { module: data.current_module_title })}</p>
      )}
      <div className="cl-progress-row">
        <span className="cl-progress-label">{t('common.overallProgress')}</span>
        <span className="cl-progress-pct">{data.progress_pct}%</span>
      </div>
      <div className="cl-progress-bar">
        <div className="cl-progress-fill" style={{ width: `${data.progress_pct}%` }} />
      </div>
      <button className="cl-resume-btn" onClick={() => navigate(`/courses/${data.course_id}/learn`)}>
        {t('common.resumeCourse')}
      </button>
    </div>
  )
}
