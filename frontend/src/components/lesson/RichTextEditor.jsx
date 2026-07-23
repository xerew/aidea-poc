import PropTypes from 'prop-types'
import { Editor } from '@tinymce/tinymce-react'
import './RichTextEditor.css'

/**
 * Self-hosted TinyMCE editor for lesson text content. Emits HTML.
 * Assets are served from /tinymce (copied by vite-plugin-static-copy), so no
 * cloud API key is required — we run under the GPL license.
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
        init={{
          menubar: false,
          statusbar: false,
          branding: false,
          promotion: false,
          height: 320,
          placeholder,
          plugins: 'lists link autolink',
          toolbar:
            'undo redo | blocks | bold italic underline | bullist numlist | link | removeformat',
          block_formats: 'Paragraph=p; Heading 2=h2; Heading 3=h3',
          content_style: 'body{font-family:inherit;font-size:15px;line-height:1.6}',
          // Content creators are trusted, but keep the output conservative.
          valid_elements:
            'p,br,strong/b,em/i,u,h2,h3,ul,ol,li,a[href|target|rel],blockquote',
        }}
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
