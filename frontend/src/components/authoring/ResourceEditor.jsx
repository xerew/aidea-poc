import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { ChevronUp, ChevronDown, Trash2, Upload, Save } from 'lucide-react'
import client from '../../api/client'
import RichTextEditor from '../lesson/RichTextEditor'
import TypeIcon from '../learner/TypeIcon'
import QuizBuilder from './QuizBuilder'
import './ResourceEditor.css'

const UPLOAD_ACCEPT = { image: '.png,.jpg,.jpeg,.gif,.webp', pdf: '.pdf' }

/**
 * Editor for one resource of an activity. In translation mode the resource
 * passed in already carries the translated values; structure (type, URL,
 * quiz answers, order, required) is locked there.
 */
export default function ResourceEditor({
  resource, index, count, locked, translating, error,
  onChange, onSave, onDelete, onMove,
}) {
  const { t } = useTranslation()
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const structureLocked = locked || translating
  const isMedia = ['image', 'video', 'pdf'].includes(resource.type)
  const typeLabel = t(`lesson.type.${resource.type}`)

  const upload = async (file) => {
    if (!file) return
    setUploadError('')
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/upload/', fd)
      onChange('url', res.data.url)
    } catch {
      setUploadError(t('authoring.moduleEditor.uploadTypeError'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className={`resource-editor${resource.isDirty ? ' resource-editor--dirty' : ''}`}>
      <div className="resource-editor-topbar">
        <span className="resource-editor-kind">
          <span className="resource-editor-index">{index + 1}</span>
          <TypeIcon type={resource.type} size={15} />
          {typeLabel}
        </span>
        {!structureLocked && (
          <div className="resource-editor-actions">
            <button type="button" className="me-media-btn" onClick={() => onMove(-1)} disabled={index === 0}
              title={t('authoring.moduleEditor.moveUp')}>
              <ChevronUp size={14} />
            </button>
            <button type="button" className="me-media-btn" onClick={() => onMove(1)} disabled={index === count - 1}
              title={t('authoring.moduleEditor.moveDown')}>
              <ChevronDown size={14} />
            </button>
            <button type="button" className="me-media-btn me-media-btn--danger" onClick={onDelete}
              disabled={count === 1} title={count === 1
                ? t('authoring.moduleEditor.resource.lastResourceHint')
                : t('authoring.moduleEditor.resource.delete')}>
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>

      <div className="resource-editor-body">
        <input
          className="lesson-field-input"
          value={resource.title ?? ''}
          disabled={locked}
          placeholder={t('authoring.moduleEditor.resource.titlePlaceholder')}
          onChange={(e) => onChange('title', e.target.value)}
        />

        {resource.type === 'text' && (
          <RichTextEditor
            value={resource.content}
            disabled={locked}
            onChange={(html) => onChange('content', html)}
            placeholder={t('authoring.moduleEditor.contentPlaceholder')}
          />
        )}

        {isMedia && (
          <>
            <div className="media-item-row">
              <input
                className="media-item-url"
                type="url"
                value={resource.url ?? ''}
                disabled={structureLocked}
                placeholder={t('authoring.moduleEditor.urlPlaceholder')}
                onChange={(e) => onChange('url', e.target.value)}
              />
              {UPLOAD_ACCEPT[resource.type] && !structureLocked && (
                <label className="lesson-upload-btn">
                  <Upload size={14} />
                  {uploading ? t('authoring.moduleEditor.uploading') : t('authoring.moduleEditor.uploadFile')}
                  <input
                    type="file"
                    hidden
                    accept={UPLOAD_ACCEPT[resource.type]}
                    disabled={uploading}
                    onChange={(e) => upload(e.target.files?.[0])}
                  />
                </label>
              )}
            </div>
            {uploadError && <p className="media-item-error">{uploadError}</p>}
            <input
              className="media-item-caption"
              value={resource.caption ?? ''}
              disabled={locked}
              placeholder={t('authoring.moduleEditor.captionPlaceholder')}
              onChange={(e) => onChange('caption', e.target.value)}
            />
          </>
        )}

        {resource.type === 'quiz' && (
          <QuizBuilder
            quizData={resource.quiz_data ?? []}
            textDisabled={locked}
            structureLocked={structureLocked}
            onChange={(next) => onChange('quiz_data', next)}
          />
        )}

        {resource.type === 'assignment' && (
          <>
            <label className="lesson-field-label">{t('authoring.moduleEditor.assignmentInstructionsLabel')}</label>
            <RichTextEditor
              value={resource.instructions}
              disabled={locked}
              onChange={(html) => onChange('instructions', html)}
              placeholder={t('authoring.moduleEditor.assignmentPlaceholder')}
            />
          </>
        )}

        <div className="resource-editor-footer">
          <label className="resource-editor-required">
            <input
              type="checkbox"
              checked={resource.is_required}
              disabled={structureLocked}
              onChange={(e) => onChange('is_required', e.target.checked)}
            />
            {t('authoring.moduleEditor.resource.required')}
          </label>
          {!locked && resource.isDirty && (
            <button type="button" className="lesson-save-btn resource-editor-save" onClick={onSave} disabled={resource.saving}>
              <Save size={14} />
              {resource.saving ? t('authoring.moduleEditor.savingLesson') : t('authoring.moduleEditor.resource.save')}
            </button>
          )}
        </div>
        {error && <p className="lesson-field-error">{error}</p>}
      </div>
    </div>
  )
}

ResourceEditor.propTypes = {
  resource: PropTypes.shape({
    id: PropTypes.number.isRequired,
    type: PropTypes.string.isRequired,
    title: PropTypes.string,
    content: PropTypes.string,
    url: PropTypes.string,
    caption: PropTypes.string,
    quiz_data: PropTypes.array,
    instructions: PropTypes.string,
    is_required: PropTypes.bool,
    isDirty: PropTypes.bool,
    saving: PropTypes.bool,
  }).isRequired,
  index: PropTypes.number.isRequired,
  count: PropTypes.number.isRequired,
  locked: PropTypes.bool.isRequired,
  translating: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onMove: PropTypes.func.isRequired,
}
