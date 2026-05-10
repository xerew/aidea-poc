import PropTypes from 'prop-types'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

RequireOnboarding.propTypes = { children: PropTypes.node.isRequired }

export default function RequireOnboarding({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (
    user.profile?.user_type === 'teacher' &&
    !user.profile?.onboarding_completed
  ) {
    return <Navigate to="/onboarding" replace />
  }
  return children
}
