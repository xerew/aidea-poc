import { useEffect, useState, useMemo, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Filter } from 'lucide-react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import './CoursesPage.css'

function pillarStyles(t) {
  return {
    'teach-with-ai':  { label: t('courses.pillarLabels.teachWithAi'),  color: 'blue' },
    'teach-for-ai':   { label: t('courses.pillarLabels.teachForAi'),   color: 'purple' },
    'teach-about-ai': { label: t('courses.pillarLabels.teachAboutAi'), color: 'green' },
  }
}

function levelForScore(score) {
  if (score <= 2) return 'beginner'
  if (score <= 4) return 'intermediate'
  return 'advanced'
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
  const { t } = useTranslation()
  const levelLabels = {
    beginner: t('common.level.beginner'),
    intermediate: t('common.level.intermediate'),
    advanced: t('common.level.advanced'),
  }
  const pillar = pillarStyles(t)[course.pillar.slug] ?? { label: course.pillar.name, color: 'blue' }
  const enrolled = course.is_enrolled

  return (
    <div className="course-card" onClick={() => navigate(`/courses/${course.id}`)} style={{ cursor: 'pointer' }}>
      <div className="course-card-top">
        <span className={`pillar-badge pillar-badge--${pillar.color}`}>{pillar.label}</span>
        <span className="level-label">{levelLabels[course.level] ?? course.level}</span>
      </div>

      <h3 className="course-title">{course.title}</h3>
      <p className="course-desc">{course.description}</p>

      <div className="course-meta">
        <span>{t('common.durationHours', { count: course.duration_hours })}</span>
        <span>{t('common.moduleCount', { count: course.module_count })}</span>
      </div>

      {enrolled && (
        <div className="course-progress">
          <div className="progress-row">
            <span>{t('common.progress')}</span>
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
        {enrolled ? t('common.continue') : t('courses.viewCourse')}
      </button>
    </div>
  )
}

export default function CoursesPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [pillars, setPillars] = useState([])
  const [error, setError]     = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const levelDefaultDone = useRef(false)

  const pillarFilter = searchParams.get('pillar') ?? ''
  const levelFilter  = searchParams.get('level')  ?? ''
  const search       = searchParams.get('search') ?? ''

  const setParam = (key, val) =>
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (val) next.set(key, val); else next.delete(key)
      return next
    }, { replace: true })

  // Teachers land with the level filter pre-set to their competency level;
  // choosing another option (incl. "All") always wins over the default.
  useEffect(() => {
    if (levelDefaultDone.current) return
    const profile = user?.profile
    if (profile?.user_type !== 'teacher' || profile?.competency_score == null) return
    levelDefaultDone.current = true
    if (searchParams.has('level')) return
    setParam('level', levelForScore(profile.competency_score))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, searchParams])

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
      .catch(() => setError(t('courses.loadError')))
  }, [t])

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
        <h1>{t('courses.title')}</h1>
        <p className="courses-subtitle">{t('courses.subtitle')}</p>
      </div>

      <div className="courses-filters">
        <Filter size={16} className="filter-icon" />
        <label>{t('courses.pillarLabel')}</label>
        <select value={pillarFilter} onChange={(e) => setParam('pillar', e.target.value)}>
          <option value="">{t('courses.all')}</option>
          {pillars.map((p) => (
            <option key={p.slug} value={p.slug}>{pillarStyles(t)[p.slug]?.label ?? p.name}</option>
          ))}
        </select>

        <label>{t('courses.levelLabel')}</label>
        <select
          value={levelFilter}
          onChange={(e) => { levelDefaultDone.current = true; setParam('level', e.target.value) }}
        >
          <option value="">{t('courses.all')}</option>
          <option value="beginner">{t('common.level.beginner')}</option>
          <option value="intermediate">{t('common.level.intermediate')}</option>
          <option value="advanced">{t('common.level.advanced')}</option>
        </select>

        <span className="courses-count">{t('courses.count', { count: filtered.length })}</span>
      </div>

      <div className="courses-grid">
        {filtered.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>
    </div>
  )
}
