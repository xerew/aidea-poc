import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircle, PlayCircle, Circle } from 'lucide-react'
import client from '../api/client'
import './PathwayPage.css'

const LEVEL_VARIANT = { beginner: 'secondary', intermediate: 'outline', advanced: 'default' }

const STATUS_ICON = {
  completed:   CheckCircle,
  in_progress: PlayCircle,
  not_started: Circle,
}

export default function PathwayPage() {
  const { t } = useTranslation()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  const levelLabels = {
    beginner: t('common.level.beginner'),
    intermediate: t('common.level.intermediate'),
    advanced: t('common.level.advanced'),
  }

  useEffect(() => {
    client.get('/pathway/')
      .then(res => setData(res.data))
      .catch(() => setError(t('pathway.loadError')))
      .finally(() => setLoading(false))
  }, [t])

  if (loading) return <div className="pathway-loading">{t('pathway.loading')}</div>
  if (error)   return <div className="pathway-error">{error}</div>

  const nextCourse  = data.courses.find(c => c.status !== 'completed')
  const progressPct = data.progress.total > 0
    ? Math.round((data.progress.completed / data.progress.total) * 100)
    : 0

  return (
    <div className="pathway-page">
      <div className="pathway-header">
        <div className="pathway-title-row">
          <h1 className="pathway-title">{data.path_name}</h1>
          <Badge variant={LEVEL_VARIANT[data.competency_level]}>
            {levelLabels[data.competency_level] ?? data.competency_level}
          </Badge>
        </div>
        <p className="pathway-description">{data.path_description}</p>
        <div className="pathway-progress-row">
          <Progress value={progressPct} className="pathway-progress-bar" />
          <span className="pathway-progress-label">
            {t('pathway.completed', { done: data.progress.completed, total: data.progress.total })}
          </span>
        </div>
      </div>

      <div className="pathway-courses">
        {data.courses.map((course, idx) => {
          const StatusIcon = STATUS_ICON[course.status] || Circle
          const isNext     = nextCourse?.id === course.id
          return (
            <Card key={course.id} className={`pathway-course-card pathway-course-${course.status}`}>
              <CardContent className="pathway-course-content">
                <div className="pathway-course-left">
                  <span className="pathway-course-number">{idx + 1}</span>
                  <StatusIcon size={20} className={`pathway-status-icon pathway-status-${course.status}`} />
                </div>
                <div className="pathway-course-info">
                  <h3 className="pathway-course-title">{course.title}</h3>
                  <div className="pathway-course-meta">
                    <span>{course.pillar_name}</span>
                    <span className="pathway-meta-dot">·</span>
                    <span>{t('pathway.durationHoursShort', { count: course.duration_hours })}</span>
                    <span className="pathway-meta-dot">·</span>
                    <Badge variant="outline" className="pathway-level-badge">{levelLabels[course.level] ?? course.level}</Badge>
                  </div>
                </div>
                {isNext && (
                  <Button asChild size="sm" className="pathway-cta">
                    <Link to={`/courses/${course.id}`}>
                      {course.status === 'in_progress' ? t('common.continue') : t('common.start')}
                    </Link>
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
