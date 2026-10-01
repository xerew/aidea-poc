import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'

const AUDIENCES = ['teachers', 'school_leaders']
const LEVELS = ['primary', 'lower_secondary', 'upper_secondary', 'cross_level']

function toggle(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
}

/**
 * Course-proposal fields shared by the create and edit pages: additional
 * Academy Pillars + cross-axis relevance, target audience, educational level
 * and recommended prior knowledge.
 *
 * `form` holds the source values. Text fields go through `textValue` /
 * `onText` so the editor can show and edit a translation; the checkbox fields
 * are structure and are locked while translating.
 */
export default function CourseProposalFields({
  pillars, form, textValue, onField, onText, locked = false, translating = false,
}) {
  const { t } = useTranslation()
  const structureLocked = locked || translating
  const otherPillars = pillars.filter((p) => p.id !== form.pillar_id)
  const extra = form.additional_pillar_ids ?? []
  const audience = form.target_audience ?? []
  const levels = form.educational_levels ?? []

  return (
    <div className="outcomes-card proposal-card">
      <h2>{t('authoring.proposal.title')}</h2>

      <div className="proposal-field">
        <span className="proposal-label">{t('authoring.proposal.additionalPillars')}</span>
        <p className="proposal-hint">{t('authoring.proposal.additionalPillarsHint')}</p>
        <div className="proposal-checks">
          {otherPillars.map((p) => (
            <label key={p.id}>
              <input
                type="checkbox"
                checked={extra.includes(p.id)}
                disabled={structureLocked}
                onChange={() => onField('additional_pillar_ids', toggle(extra, p.id))}
              />
              {p.name}
            </label>
          ))}
        </div>
      </div>

      <div className="proposal-field">
        <label className="proposal-label" htmlFor="cross-axis">{t('authoring.proposal.crossAxis')}</label>
        <p className="proposal-hint">{t('authoring.proposal.crossAxisHint')}</p>
        <textarea
          id="cross-axis"
          className="editor-desc-input proposal-textarea"
          rows={2}
          value={textValue('cross_axis_relevance')}
          disabled={locked}
          onChange={(e) => onText('cross_axis_relevance', e.target.value)}
        />
      </div>

      <div className="proposal-field">
        <span className="proposal-label">{t('authoring.proposal.targetAudience')}</span>
        <p className="proposal-hint">{t('authoring.proposal.selectAll')}</p>
        <div className="proposal-checks">
          {AUDIENCES.map((a) => (
            <label key={a}>
              <input
                type="checkbox"
                checked={audience.includes(a)}
                disabled={structureLocked}
                onChange={() => onField('target_audience', toggle(audience, a))}
              />
              {t(`authoring.proposal.audience.${a}`)}
            </label>
          ))}
          <label className="proposal-other">
            {t('authoring.proposal.other')}
            <input
              value={textValue('target_audience_other')}
              disabled={locked}
              placeholder={t('authoring.proposal.otherPlaceholder')}
              onChange={(e) => onText('target_audience_other', e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="proposal-field">
        <span className="proposal-label">{t('authoring.proposal.educationalLevel')}</span>
        <p className="proposal-hint">{t('authoring.proposal.educationalLevelHint')}</p>
        <div className="proposal-checks">
          {LEVELS.map((l) => (
            <label key={l}>
              <input
                type="checkbox"
                checked={levels.includes(l)}
                disabled={structureLocked}
                onChange={() => onField('educational_levels', toggle(levels, l))}
              />
              {t(`authoring.proposal.level.${l}`)}
            </label>
          ))}
          <label className="proposal-other">
            {t('authoring.proposal.other')}
            <input
              value={textValue('educational_level_other')}
              disabled={locked}
              placeholder={t('authoring.proposal.otherPlaceholder')}
              onChange={(e) => onText('educational_level_other', e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="proposal-field">
        <label className="proposal-label" htmlFor="prior-knowledge">{t('authoring.proposal.priorKnowledge')}</label>
        <textarea
          id="prior-knowledge"
          className="editor-desc-input proposal-textarea"
          rows={2}
          value={textValue('prior_knowledge')}
          disabled={locked}
          placeholder={t('authoring.proposal.priorKnowledgePlaceholder')}
          onChange={(e) => onText('prior_knowledge', e.target.value)}
        />
      </div>
    </div>
  )
}

CourseProposalFields.propTypes = {
  pillars: PropTypes.arrayOf(PropTypes.shape({ id: PropTypes.number, name: PropTypes.string })).isRequired,
  form: PropTypes.shape({
    pillar_id: PropTypes.number,
    additional_pillar_ids: PropTypes.arrayOf(PropTypes.number),
    target_audience: PropTypes.arrayOf(PropTypes.string),
    educational_levels: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  textValue: PropTypes.func.isRequired,
  onField: PropTypes.func.isRequired,
  onText: PropTypes.func.isRequired,
  locked: PropTypes.bool,
  translating: PropTypes.bool,
}
