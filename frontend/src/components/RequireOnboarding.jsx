import PropTypes from 'prop-types'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

RequireOnboarding.propTypes = { children: PropTypes.node.isRequired }

export default function RequireOnboarding({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  // Every role completes onboarding first: it sets up the pathway and
  // recommendations the same way for teachers, creators, partners and admins.
  if (user.profile && !user.profile.onboarding_completed) {
    return <Navigate to="/onboarding" replace />
  }
  return children
}
