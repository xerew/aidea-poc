import { useEffect, useState, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Filter } from 'lucide-react'
import PropTypes from 'prop-types'
import client from '../api/client'
import './CoursesPage.css'

const PILLAR_STYLES = {
  'teach-with-ai': { label: 'Teach with AI', color: 'blue' },
  'teach-for-ai':  { label: 'Teach for AI',  color: 'purple' },
  'teach-about-ai':{ label: 'Teach about AI',color: 'green' },
}

const LEVEL_LABELS = {
  beginner:     'Beginner',
  intermediate: 'Intermediate',
  advanced:     'Advanced',
}

CourseCard.propTypes = {
  course: PropTypes.shape({
    id: PropTypes.number,
    title: PropTypes.string,
    description: PropTypes.string,
    level: PropTypes.string,
    duration_hours: PropTypes.number,
    module_count: PropTypes.number,
    is_enrolled: PropTypes.bool,
    progress_pct: PropTypes.number,
    pillar: PropTypes.shape({ slug: PropTypes.string, name: PropTypes.string }),
  }),
}

function CourseCard({ course }) {
  const navigate = useNavigate()
  const pillar = PILLAR_STYLES[course.pillar.slug] ?? { label: course.pillar.name, color: 'blue' }
  const enrolled = course.is_enrolled

  return (
    <div className="course-card" onClick={() => navigate(`/courses/${course.id}`)} style={{ cursor: 'pointer' }}>
      <div className="course-card-top">
        <span className={`pillar-badge pillar-badge--${pillar.color}`}>{pillar.label}</span>
        <span className="level-label">{LEVEL_LABELS[course.level] ?? course.level}</span>
      </div>

      <h3 className="course-title">{course.title}</h3>
      <p className="course-desc">{course.description}</p>

      <div className="course-meta">
        <span>{course.duration_hours} hours</span>
        <span>{course.module_count} modules</span>
      </div>

      {enrolled && (
        <div className="course-progress">
          <div className="progress-row">
            <span>Progress</span>
            <span>{course.progress_pct}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${course.progress_pct}%` }} />
          </div>
        </div>
      )}

      <button
        className={`course-btn ${enrolled ? 'course-btn--dark' : 'course-btn--outline'}`}
        onClick={(e) => { e.stopPropagation(); navigate(`/courses/${course.id}`) }}
      >
        {enrolled ? 'Continue' : 'View Course'}
      </button>
    </div>
  )
}

export default function CoursesPage() {
  const [courses, setCourses] = useState([])
  const [pillars, setPillars] = useState([])
  const [error, setError]     = useState('')
  const [searchParams, setSearchParams] = useSearchParams()

  const pillarFilter = searchParams.get('pillar') ?? ''
  const levelFilter  = searchParams.get('level')  ?? ''
  const search       = searchParams.get('search') ?? ''

  const setParam = (key, val) =>
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (val) next.set(key, val); else next.delete(key)
      return next
    }, { replace: true })

  useEffect(() => {
    client.get('/courses/')
      .then((res) => {
        setCourses(res.data)
        const seen = new Set()
        const unique = []
        res.data.forEach((c) => {
          if (!seen.has(c.pillar.slug)) {
            seen.add(c.pillar.slug)
            unique.push(c.pillar)
          }
        })
        setPillars(unique)
      })
      .catch(() => setError('Failed to load courses.'))
  }, [])

  // client-side filter for instant response
  const filtered = useMemo(() => {
    return courses.filter((c) => {
      if (pillarFilter && c.pillar.slug !== pillarFilter) return false
      if (levelFilter  && c.level       !== levelFilter)  return false
      if (search && !c.title.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [courses, pillarFilter, levelFilter, search])

  if (error) return <p className="page-error">{error}</p>

  return (
    <div className="courses-page">
      <div className="courses-header">
        <h1>Courses</h1>
        <p className="courses-subtitle">Explore our comprehensive AI training curriculum</p>
      </div>

      <div className="courses-filters">
        <Filter size={16} className="filter-icon" />
        <label>Pillar:</label>
        <select value={pillarFilter} onChange={(e) => setParam('pillar', e.target.value)}>
          <option value="">All</option>
          {pillars.map((p) => (
            <option key={p.slug} value={p.slug}>{p.name}</option>
          ))}
        </select>

        <label>Level:</label>
        <select value={levelFilter} onChange={(e) => setParam('level', e.target.value)}>
          <option value="">All</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>

        <span className="courses-count">{filtered.length} courses</span>
      </div>

      <div className="courses-grid">
        {filtered.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>
    </div>
  )
}
