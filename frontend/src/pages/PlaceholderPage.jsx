import PropTypes from 'prop-types'

PlaceholderPage.propTypes = { title: PropTypes.string }

export default function PlaceholderPage({ title }) {
  return (
    <div style={{ color: '#6b7280', paddingTop: '2rem' }}>
      <h2 style={{ color: '#111827' }}>{title}</h2>
      <p>Coming soon.</p>
    </div>
  )
}
