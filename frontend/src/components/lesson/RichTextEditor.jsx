import PropTypes from 'prop-types'
import { Editor } from '@tinymce/tinymce-react'
import client from '../../api/client'
import { makeImageUploader } from '../../lib/richText'
import { editorInit } from '../../lib/editorSetup'
// The learner-view stylesheet (fonts included), injected into the editor frame
// so authors see exactly what learners will see.
import richContentCss from '../../styles/richContent.css?inline'
import './RichTextEditor.css'

const uploadImage = makeImageUploader(client)
const contentStyle = `${richContentCss}\nbody{margin:1rem;font-size:15px}`

/**
 * Self-hosted TinyMCE editor for lesson text content. Emits HTML.
 * Assets are served from /tinymce (copied by vite-plugin-static-copy), so no
 * cloud API key is required — we run under the GPL license.
 * Configuration: lib/editorSetup.js; allowed formatting: lib/richTextStyles.js.
 */
export default function RichTextEditor({ value, onChange, disabled = false, placeholder = '' }) {
  return (
    <div className="rich-text-editor">
      <Editor
        tinymceScriptSrc="/tinymce/tinymce.min.js"
        licenseKey="gpl"
        value={value ?? ''}
        disabled={disabled}
        onEditorChange={(html) => onChange(html)}
        init={editorInit({ placeholder, uploadImage, contentStyle })}
      />
    </div>
  )
}

RichTextEditor.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  placeholder: PropTypes.string,
}
