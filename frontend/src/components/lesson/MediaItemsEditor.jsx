import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2, Upload, ChevronUp, ChevronDown, Type } from 'lucide-react'
import client from '../../api/client'
import RichTextEditor from './RichTextEditor'
import './MediaItemsEditor.css'

/**
 * Ordered block editor for a media lesson: interleave rich-text blocks
 * ({type: 'text', html}) with media items of the lesson's own type
 * ({type: fixedType, url, caption}). An image lesson holds only images, etc.
 */
export default function MediaItemsEditor({ items, onChange, disabled = false, fixedType }) {
  const { t } = useTranslation()
  const [uploadingIdx, setUploadingIdx] = useState(null)
  const [errors, setErrors] = useState({})  // per-item upload error message

  const update = (i, patch) =>
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i))
  const addText = () => onChange([...items, { type: 'text', html: '' }])
  const addMedia = () => onChange([...items, { type: fixedType, url: '', caption: '' }])

  const move = (i, dir) => {
    const j = i + dir
    if (j < 0 || j >= items.length) return
    const copy = [...items]
    const tmp = copy[i]
    copy[i] = copy[j]
    copy[j] = tmp
    onChange(copy)
  }

  const upload = async (i, file) => {
    if (!file) return
    setErrors(prev => { const n = { ...prev }; delete n[i]; return n })
    setUploadingIdx(i)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/upload/', fd)
      update(i, { url: res.data.url })
    } catch {
      setErrors(prev => ({ ...prev, [i]: t('authoring.moduleEditor.uploadTypeError') }))
    } finally {
      setUploadingIdx(null)
    }
  }

  const mediaLabel = t(`lesson.type.${fixedType}`)

  return (
    <div className="media-items">
      <label className="lesson-field-label">{t('authoring.moduleEditor.mediaLabel')}</label>
      <p className="lesson-field-hint">{t('authoring.moduleEditor.mediaHint')}</p>

      {items.map((item, i) => (
        <div key={i} className="media-item">
          <div className="media-item-topbar">
            <span className="media-item-kind">
              {item.type === 'text' ? t('lesson.type.text') : t(`lesson.type.${item.type}`)}
            </span>
            {!disabled && (
              <div className="media-item-actions">
                <button className="me-media-btn" onClick={() => move(i, -1)} disabled={i === 0} title={t('authoring.moduleEditor.moveUp')}>
                  <ChevronUp size={14} />
                </button>
                <button className="me-media-btn" onClick={() => move(i, 1)} disabled={i === items.length - 1} title={t('authoring.moduleEditor.moveDown')}>
                  <ChevronDown size={14} />
                </button>
                <button className="me-media-btn me-media-btn--danger" onClick={() => remove(i)} title={t('common.delete')}>
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>

          {item.type === 'text' ? (
            <RichTextEditor
              value={item.html}
              disabled={disabled}
              onChange={(html) => update(i, { html })}
            />
          ) : (
            <>
              <div className="media-item-row">
                <input
                  className="media-item-url"
                  type="url"
                  value={item.url}
                  disabled={disabled}
                  placeholder={t('authoring.moduleEditor.urlPlaceholder')}
                  onChange={(e) => update(i, { url: e.target.value })}
                />
                {['image', 'pdf'].includes(item.type) && !disabled && (
                  <label className="lesson-upload-btn">
                    <Upload size={14} />
                    {uploadingIdx === i ? t('authoring.moduleEditor.uploading') : t('authoring.moduleEditor.uploadFile')}
                    <input
                      type="file"
                      hidden
                      accept={item.type === 'pdf' ? '.pdf' : '.png,.jpg,.jpeg,.gif,.webp'}
                      disabled={uploadingIdx !== null}
                      onChange={(e) => upload(i, e.target.files?.[0])}
                    />
                  </label>
                )}
              </div>
              {errors[i] && <p className="media-item-error">{errors[i]}</p>}
              <input
                className="media-item-caption"
                value={item.caption ?? ''}
                disabled={disabled}
                placeholder={t('authoring.moduleEditor.captionPlaceholder')}
                onChange={(e) => update(i, { caption: e.target.value })}
              />
            </>
          )}
        </div>
      ))}

      {!disabled && (
        <div className="media-add-row">
          <button className="add-dashed-btn" onClick={addText}>
            <Type size={14} /> {t('authoring.moduleEditor.addText')}
          </button>
          <button className="add-dashed-btn" onClick={addMedia}>
            <Plus size={14} /> {t('authoring.moduleEditor.addMediaOfType', { type: mediaLabel })}
          </button>
        </div>
      )}
    </div>
  )
}

MediaItemsEditor.propTypes = {
  items: PropTypes.array.isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  fixedType: PropTypes.string.isRequired,
}
