import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, CheckCircle2, Circle, XCircle } from 'lucide-react'
import client from '../../api/client'
import TypeIcon from '../learner/TypeIcon'
import { formatDate, formatDuration, formatH5PAttempt, itemTime } from './format'

ResourceDetails.propTypes = { r: PropTypes.object.isRequired }
function ResourceDetails({ r }) {
  const { t } = useTranslation()
  const bits = []
  if (r.quiz_score != null) bits.push(t('analytics.course.detail.score', { pct: Math.round(r.quiz_score * 100) }))
  if (r.h5p_attempts) bits.push(t('analytics.course.detail.attempts', { count: r.h5p_attempts }))
  if (r.video_pct != null) bits.push(t('analytics.course.detail.watched', { pct: r.video_pct }))
  if (r.scroll_pct != null) bits.push(t('analytics.course.detail.scrolled', { pct: r.scroll_pct }))
  if (r.pdf_opened) bits.push(t('analytics.course.detail.opened'))
  if (r.image_opened) bits.push(t('analytics.course.detail.opened'))
  if (r.pdf_downloaded) bits.push(t('analytics.course.detail.downloaded'))
  if (r.assignment_status) bits.push(t(`analytics.course.detail.assignment.${r.assignment_status}`))
  return (
    <>
      {bits.length > 0 && <span>{bits.join(' · ')}</span>}
      {r.quiz_answers?.length > 0 && (
        <ol className="acp-answers">
          {r.quiz_answers.map(a => (
            <li key={a.index}>
              {a.is_correct ? <CheckCircle2 size={13} className="acp-right" /> : <XCircle size={13} className="acp-wrong" />}
              <span className="acp-answer-q">{a.question}</span>
              <span className="acp-answer-a">{a.selected_text ?? '—'}</span>
              {a.seconds != null && <span className="acp-answer-t">{t('analytics.course.detail.answerTime', { s: a.seconds })}</span>}
            </li>
          ))}
        </ol>
      )}
      {r.h5p?.attempts?.length > 0 && (
        <p className="acp-notes">{r.h5p.attempts.map(a => formatH5PAttempt(a, t)).join("  |  ")}</p>
      )}
      {r.h5p?.answers?.length > 0 && (
        <ol className="acp-answers">
          {r.h5p.answers.map((a, i) => (
            <li key={i}>
              {a.correct === true ? <CheckCircle2 size={13} className="acp-right" />
                : a.correct === false ? <XCircle size={13} className="acp-wrong" />
                  : <Circle size={13} className="acp-muted" />}
              <span className="acp-answer-t">{t('analytics.course.detail.attemptN', { n: a.attempt })}</span>
              <span className="acp-answer-q">{a.question}</span>
              <span className="acp-answer-a">{a.response || '—'}</span>
              {a.seconds != null && <span className="acp-answer-t">{t('analytics.course.detail.answerTime', { s: a.seconds })}</span>}
            </li>
          ))}
        </ol>
      )}
    </>
  )
}

LearnerTimeline.propTypes = {
  courseId: PropTypes.string.isRequired,
  userId: PropTypes.number.isRequired,
  onBack: PropTypes.func.isRequired,
}

export default function LearnerTimeline({ courseId, userId, onBack }) {
  const { t, i18n } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client.get(`/analytics/courses/${courseId}/learners/${userId}/`)
      .then(res => setData(res.data))
      .catch(() => setError(t('analytics.loadError')))
  }, [courseId, userId, t])

  const back = (
    <button className="acp-back" onClick={onBack}><ArrowLeft size={14} /> {t('analytics.course.backToLearners')}</button>
  )
  if (error) return <>{back}<p className="page-error">{error}</p></>
  if (!data) return <>{back}<p className="page-loading">{t('common.loading')}</p></>

  const { learner } = data
  return (
    <div className="acp-timeline">
      {back}
      <div className="acp-timeline-head">
        <h2>{learner.name}</h2>
        <span className="acp-learner-email">{learner.email}</span>
        <span className={`acp-status acp-status--${learner.status}`}>{t(`analytics.course.status.${learner.status}`)}</span>
        <span>{learner.progress_pct}%</span>
        <span>{t('analytics.course.totals', {
          active: formatDuration(learner.active_s, t), onScreen: formatDuration(learner.visible_s, t), visits: learner.visits,
        })}</span>
      </div>
      {data.modules.map(m => (
        <section key={m.id} className="acp-tl-module">
          <h3>
            {t('common.moduleLabel', { order: m.order, title: m.title })}
            <span className="acp-tl-meta">{m.pct ?? 0}% · {itemTime(m.active_s, m.visits, null, t)}</span>
          </h3>
          {m.activities.map(a => (
            <div key={a.id} className="acp-tl-activity">
              <h4>
                {a.done ? <CheckCircle2 size={15} className="acp-right" /> : <Circle size={15} className="acp-muted" />}
                {a.title}
                <span className="acp-tl-meta">{itemTime(a.active_s, a.visits, null, t)}</span>
              </h4>
              <div className="acp-table-wrap">
                <table className="acp-table acp-table--compact">
                  <thead>
                    <tr>
                      <th>{t('analytics.course.col.resource')}</th>
                      <th className="acp-num">{t('analytics.course.col.active')}</th>
                      <th className="acp-num">{t('analytics.course.col.onScreen')}</th>
                      <th className="acp-num">{t('analytics.course.col.visits')}</th>
                      <th>{t('analytics.course.col.firstOpened')}</th>
                      <th>{t('analytics.course.col.completed')}</th>
                      <th>{t('analytics.course.col.details')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.resources.map(r => (
                      <tr key={r.id}>
                        <td><span className="acp-resource-title"><TypeIcon type={r.type} size={14} /> {r.title}</span></td>
                        <td className="acp-num">{itemTime(r.active_s, r.visits, r.completed_at, t)}</td>
                        <td className="acp-num">{r.visits ? formatDuration(r.visible_s, t) : '—'}</td>
                        <td className="acp-num">{r.visits}</td>
                        <td>{formatDate(r.first_opened, i18n.language)}</td>
                        <td>{formatDate(r.completed_at, i18n.language)}</td>
                        <td><ResourceDetails r={r} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  )
}
