import PropTypes from 'prop-types'
import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, Lock, GraduationCap, MapPin, School, BookOpen, CalendarDays, MessageCircle,
} from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { MESSAGING_ENABLED } from '../config'
import { getAvatarSrc } from '../lib/avatar'
import { getFlagEmoji, COUNTRIES } from '../data/countries'
import './PublicProfilePage.css'

const ROLE_KEYS = {
  teacher: 'teacher',
  content_creator: 'contentCreator',
  aidea_partner: 'aideaPartner',
  admin: 'admin',
}

function countryName(code) {
  return COUNTRIES.find(c => c.code === code)?.name || code
}

function Identity({ profile }) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const avatarSrc = getAvatarSrc(profile)
  const roleKey = ROLE_KEYS[profile.user_type]
  const isMe = user?.id === profile.id
  return (
    <div className="pp-identity">
      {avatarSrc ? (
        <img className="pp-avatar-img" src={avatarSrc} alt={profile.name} />
      ) : (
        <div className="pp-avatar">{profile.avatar_initials || '?'}</div>
      )}
      <div className="pp-identity-text">
        <h1 className="pp-name">{profile.name}</h1>
        {roleKey && (
          <span className={`pp-role pp-role--${profile.user_type}`}>
            {t(`publicProfile.roles.${roleKey}`)}
          </span>
        )}
      </div>
      {!isMe && MESSAGING_ENABLED && (
        <Link to={`/messages/${profile.id}`} className="pp-message-btn">
          <MessageCircle size={16} /> {t('publicProfile.sendMessage')}
        </Link>
      )}
    </div>
  )
}

Identity.propTypes = { profile: PropTypes.object.isRequired }

function DetailRow({ icon: Icon, children }) {
  return (
    <li className="pp-detail">
      <Icon size={16} className="pp-detail-icon" />
      <span>{children}</span>
    </li>
  )
}

DetailRow.propTypes = { icon: PropTypes.elementType.isRequired, children: PropTypes.node }

export default function PublicProfilePage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  // Go back to wherever the user came from; fall back to Courses if there's
  // no history (e.g. the profile link was opened directly).
  const goBack = () => (window.history.length > 1 ? navigate(-1) : navigate('/courses'))
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [loadedId, setLoadedId] = useState(id)

  // Reset to the loading state when navigating between profiles (id change).
  if (id !== loadedId) {
    setLoadedId(id)
    setProfile(null)
    setLoading(true)
    setError('')
  }

  useEffect(() => {
    let active = true
    client.get(`/users/${id}/profile/`)
      .then(res => { if (active) setProfile(res.data) })
      .catch(err => { if (active) setError(err?.response?.status === 404
        ? t('publicProfile.notFound')
        : t('publicProfile.loadFailed')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id, t])

  if (loading) return <div className="pp-page"><p className="pp-loading">{t('common.loading')}</p></div>
  if (error) return (
    <div className="pp-page">
      <button type="button" onClick={goBack} className="pp-back"><ArrowLeft size={16} /> {t('common.back')}</button>
      <p className="pp-message">{error}</p>
    </div>
  )
  if (!profile) return null

  const details = []
  if (profile.subject_name) {
    details.push(
      <DetailRow key="subject" icon={GraduationCap}>
        {profile.subject_name}
        {profile.teaching_level ? ` · ${profile.teaching_level}` : ''}
      </DetailRow>,
    )
  }
  if (profile.school) details.push(<DetailRow key="school" icon={School}>{profile.school}</DetailRow>)
  if (profile.country) {
    details.push(
      <DetailRow key="country" icon={MapPin}>
        {getFlagEmoji(profile.country)} {countryName(profile.country)}
      </DetailRow>,
    )
  }
  if (profile.member_since) {
    details.push(
      <DetailRow key="since" icon={CalendarDays}>
        {t('publicProfile.memberSince', { date: new Date(profile.member_since).toLocaleDateString() })}
      </DetailRow>,
    )
  }

  return (
    <div className="pp-page">
      <button type="button" onClick={goBack} className="pp-back"><ArrowLeft size={16} /> {t('common.back')}</button>

      <section className="pp-card">
        <Identity profile={profile} />

        {!profile.is_public ? (
          <div className="pp-private">
            <Lock size={18} />
            <p>{t('publicProfile.private')}</p>
          </div>
        ) : (
          <>
            {profile.bio && <p className="pp-bio">{profile.bio}</p>}
            {details.length > 0 && <ul className="pp-details">{details}</ul>}

            {profile.competency && (
              <div className="pp-block">
                <h2 className="pp-block-title">{t('publicProfile.competencyTitle')}</h2>
                <span className={`pp-competency pp-competency--${profile.competency.level}`}>
                  {t(`publicProfile.competency.${profile.competency.level}`)}
                </span>
              </div>
            )}

            {profile.progress && (
              <div className="pp-block">
                <h2 className="pp-block-title">{t('publicProfile.progressTitle')}</h2>
                <div className="pp-stats">
                  <div className="pp-stat">
                    <span className="pp-stat-num">{profile.progress.completed}</span>
                    <span className="pp-stat-label">{t('publicProfile.completed')}</span>
                  </div>
                  <div className="pp-stat">
                    <span className="pp-stat-num">{profile.progress.in_progress}</span>
                    <span className="pp-stat-label">{t('publicProfile.inProgress')}</span>
                  </div>
                </div>
              </div>
            )}

            {profile.authored_courses && (
              <div className="pp-block">
                <h2 className="pp-block-title">{t('publicProfile.authoredTitle')}</h2>
                {profile.authored_courses.length === 0 ? (
                  <p className="pp-empty">{t('publicProfile.noCourses')}</p>
                ) : (
                  <ul className="pp-courses">
                    {profile.authored_courses.map(c => (
                      <li key={c.id}>
                        <Link to={`/courses/${c.id}`} className="pp-course-link">
                          <BookOpen size={15} />
                          <span className="pp-course-title">{c.title}</span>
                          <span className="pp-course-pillar">{c.pillar_name}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
