import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Download, Info } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import ContentTree from '../components/analytics/ContentTree'
import LearnersTable from '../components/analytics/LearnersTable'
import LearnerTimeline from '../components/analytics/LearnerTimeline'
import { downloadXlsx } from '../components/analytics/download'
import './AnalyticsCoursePage.css'

const TABS = ['content', 'learners']

export default function AnalyticsCoursePage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { user } = useAuth()
  const isCreator = ['content_creator', 'aidea_partner', 'admin'].includes(user?.profile?.user_type)
  const [tab, setTab] = useState('content')
  const [content, setContent] = useState(null)
  const [learners, setLearners] = useState(null)
  const [learnerId, setLearnerId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isCreator) return
    Promise.all([
      client.get(`/analytics/courses/${id}/content/`),
      client.get(`/analytics/courses/${id}/learners/`),
    ])
      .then(([c, l]) => { setContent(c.data); setLearners(l.data.learners) })
      .catch(err => setError(err.response?.status === 404 ? t('analytics.course.notFound') : t('analytics.loadError')))
  }, [id, isCreator, t])

  if (!isCreator) return <div className="an-restricted"><p>{t('analytics.restricted')}</p></div>
  if (error) return <p className="page-error">{error}</p>
  if (!content || !learners) return <p className="page-loading">{t('common.loading')}</p>

  const exportCourse = () => downloadXlsx(`/analytics/courses/${id}/export/`, {}, `course-${id}-analytics.xlsx`).catch(() => {})

  return (
    <div className="acp-page">
      <Link className="acp-back" to="/analytics"><ArrowLeft size={14} /> {t('analytics.course.back')}</Link>
      <div className="acp-header">
        <div>
          <h1 className="acp-title">{content.course.title}</h1>
          <p className="acp-subtitle">{t('analytics.course.learnersCount', { count: content.learners })}</p>
        </div>
        <button className="an-export-btn" onClick={exportCourse}><Download size={15} /> {t('analytics.downloadExcel')}</button>
      </div>
      <p className="acp-help"><Info size={14} /> {t('analytics.course.help')}</p>

      {learnerId ? (
        <LearnerTimeline key={learnerId} courseId={id} userId={learnerId} onBack={() => setLearnerId(null)} />
      ) : (
        <>
          <div className="acp-tabs" role="tablist">
            {TABS.map(k => (
              <button key={k} role="tab" aria-selected={tab === k} className={`acp-tab ${tab === k ? 'acp-tab--active' : ''}`} onClick={() => setTab(k)}>
                {t(`analytics.course.tabs.${k}`)}
              </button>
            ))}
          </div>
          {tab === 'content'
            ? <ContentTree tree={content} />
            : <LearnersTable learners={learners} onOpen={setLearnerId} />}
        </>
      )}
    </div>
  )
}
