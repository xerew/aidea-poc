import { useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2, Upload, ChevronUp, ChevronDown } from 'lucide-react'
import client from '../../api/client'
import './MediaItemsEditor.css'

const TYPES = ['image', 'video', 'pdf']

/**
 * Manages a lesson's ordered media items: each is {type, url, caption}.
 * When `fixedType` is set the whole list is that one media type (an image
 * lesson holds only images, etc.) and the per-item type dropdown is hidden.
 * Images/PDFs can be uploaded or linked; videos are a URL.
 */
export default function MediaItemsEditor({ items, onChange, disabled = false, fixedType = null }) {
  const { t } = useTranslation()
  const [uploadingIdx, setUploadingIdx] = useState(null)

  const update = (i, patch) =>
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))
  const remove = (i) => onChange(items.filter((_, idx) => idx !== i))
  const add = () => onChange([...items, { type: fixedType ?? 'image', url: '', caption: '' }])

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
    setUploadingIdx(i)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/upload/', fd)
      update(i, { url: res.data.url })
    } catch { /* ignore */ }
    finally { setUploadingIdx(null) }
  }

  return (
    <div className="media-items">
      <label className="lesson-field-label">{t('authoring.moduleEditor.mediaLabel')}</label>
      <p className="lesson-field-hint">{t('authoring.moduleEditor.mediaHint')}</p>

      {items.map((item, i) => (
        <div key={i} className="media-item">
          <div className="media-item-row">
            {!fixedType && (
              <select
                className="media-item-type"
                value={item.type}
                disabled={disabled}
                onChange={(e) => update(i, { type: e.target.value })}
              >
                {TYPES.map((ty) => <option key={ty} value={ty}>{t(`lesson.type.${ty}`)}</option>)}
              </select>
            )}
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
                  accept={item.type === 'pdf' ? '.pdf' : 'image/*'}
                  disabled={uploadingIdx !== null}
                  onChange={(e) => upload(i, e.target.files?.[0])}
                />
              </label>
            )}
          </div>
          <div className="media-item-row">
            <input
              className="media-item-caption"
              value={item.caption ?? ''}
              disabled={disabled}
              placeholder={t('authoring.moduleEditor.captionPlaceholder')}
              onChange={(e) => update(i, { caption: e.target.value })}
            />
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
        </div>
      ))}

      {!disabled && (
        <button className="add-dashed-btn" onClick={add}>
          <Plus size={14} /> {t('authoring.moduleEditor.addMedia')}
        </button>
      )}
    </div>
  )
}

MediaItemsEditor.propTypes = {
  items: PropTypes.array.isRequired,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  fixedType: PropTypes.string,
}
