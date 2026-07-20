import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'

PlaceholderPage.propTypes = { title: PropTypes.string }

export default function PlaceholderPage({ title }) {
  const { t } = useTranslation()
  return (
    <div style={{ color: '#6b7280', paddingTop: '2rem' }}>
      <h2 style={{ color: '#111827' }}>{title}</h2>
      <p>{t('common.comingSoon')}</p>
    </div>
  )
}
