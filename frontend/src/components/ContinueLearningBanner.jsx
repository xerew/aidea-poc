import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
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
  if (!data) return null
  return (
    <div className="cl-banner">
      <p className="cl-label">Continue Learning</p>
      <h2 className="cl-title">{data.course_title}</h2>
      {data.current_module_title && (
        <p className="cl-next-module">Next: {data.current_module_title}</p>
      )}
      <div className="cl-progress-row">
        <span className="cl-progress-label">Overall Progress</span>
        <span className="cl-progress-pct">{data.progress_pct}%</span>
      </div>
      <div className="cl-progress-bar">
        <div className="cl-progress-fill" style={{ width: `${data.progress_pct}%` }} />
      </div>
      <button className="cl-resume-btn" onClick={() => navigate(`/courses/${data.course_id}/learn`)}>
        Resume Course
      </button>
    </div>
  )
}
