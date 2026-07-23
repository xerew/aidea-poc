import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import './SubjectPicker.css'

/**
 * Toggleable chip list for selecting the subjects a course targets.
 * `selectedIds` is an array of subject ids; `onChange` receives the new array.
 */
export default function SubjectPicker({ subjects, selectedIds, onChange, disabled = false }) {
  const { t } = useTranslation()
  const selected = new Set(selectedIds)

  const toggle = (id) => {
    if (disabled) return
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChange([...next])
  }

  return (
    <div className="subject-picker">
      <h2>{t('authoring.editor.subjectsLabel')}</h2>
      <p className="subject-picker-hint">{t('authoring.editor.subjectsHint')}</p>
      <div className="subject-picker-chips">
        {subjects.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`subject-chip${selected.has(s.id) ? ' subject-chip--on' : ''}`}
            onClick={() => toggle(s.id)}
            disabled={disabled}
          >
            {s.name}
          </button>
        ))}
      </div>
    </div>
  )
}

SubjectPicker.propTypes = {
  subjects: PropTypes.array.isRequired,
  selectedIds: PropTypes.array.isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}
