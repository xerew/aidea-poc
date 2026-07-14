import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Clock, Pencil, Plus } from 'lucide-react'
import client from '../api/client'
import './AuthoringPage.css'

const PILLAR_COLOR = {
  'teach-with-ai':  'blue',
  'teach-for-ai':   'purple',
  'teach-about-ai': 'green',
}

const LEVEL_LABELS = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }

export default function AuthoringPage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get('/authoring/courses/')
      .then((res) => setCourses(res.data))
      .catch(() => setError('Failed to load courses. Make sure your account has Content Creator access.'))
      .finally(() => setLoading(false))
  }, [])

  if (error) return <p className="page-error">{error}</p>
  if (loading) return <p className="page-loading">Loading…</p>

  const byPillar = courses.reduce((acc, course) => {
    const key = course.pillar.id
    if (!acc[key]) acc[key] = { pillar: course.pillar, courses: [] }
    acc[key].courses.push(course)
    return acc
  }, {})

  return (
    <div className="authoring-page">
      <div className="authoring-header">
        <div>
          <h1 className="authoring-title">Course Authoring</h1>
          <p className="authoring-subtitle">Select a course to edit its content.</p>
        </div>
        <button className="new-course-btn" onClick={() => navigate('/authoring/courses/new')}>
          <Plus size={15} /> New Course
        </button>
      </div>

      {courses.length === 0 && (
        <p className="authoring-empty">No courses yet. Create your first one!</p>
      )}

      {Object.values(byPillar).map(({ pillar, courses: pillarCourses }) => (
        <section key={pillar.id} className="authoring-pillar-section">
          <span className={`pillar-badge pillar-badge--${PILLAR_COLOR[pillar.slug] ?? 'blue'}`}>
            {pillar.name}
          </span>
          <div className="authoring-course-list">
            {pillarCourses.map((course) => (
              <div key={course.id} className="authoring-course-row">
                <div className="authoring-course-info">
                  <div className="authoring-course-title-row">
                    <p className="authoring-course-title">{course.title}</p>
                    <span className={`status-badge ${course.is_published ? 'status-badge--published' : 'status-badge--draft'}`}>
                      {course.is_published ? 'Published' : 'Draft'}
                    </span>
                  </div>
                  <div className="authoring-course-meta">
                    <span><Clock size={13} /> {course.duration_hours}h</span>
                    <span><BookOpen size={13} /> {course.module_count} modules</span>
                    <span>{LEVEL_LABELS[course.level] ?? course.level}</span>
                  </div>
                  <p className="course-card-author">By {course.created_by_name}</p>
                </div>
                <button
                  className="edit-btn"
                  onClick={() => navigate(`/authoring/courses/${course.id}`)}
                >
                  <Pencil size={14} /> {course.is_published ? 'View' : 'Edit'}
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
