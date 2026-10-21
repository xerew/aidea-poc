import PropTypes from 'prop-types'
import { Editor } from '@tinymce/tinymce-react'
import client from '../../api/client'
import { RICH_TEXT_VALID_ELEMENTS } from '../../lib/richText'
import './RichTextEditor.css'

// TinyMCE image upload: same endpoint and checks as image resources.
async function uploadImage(blobInfo) {
  const form = new FormData()
  form.append('file', blobInfo.blob(), blobInfo.filename())
  try {
    const res = await client.post('/authoring/upload/', form)
    return res.data.url
  } catch (err) {
    throw new Error(err.response?.data?.error ?? 'Upload failed.')
  }
}

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
          plugins: 'lists link autolink table image',
          toolbar:
            'undo redo | blocks | bold italic underline | bullist numlist | link image table | removeformat',
          table_toolbar: 'tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol | tablemergecells tablesplitcells',
          table_appearance_options: false,
          table_advtab: false,
          table_cell_advtab: false,
          table_row_advtab: false,
          table_default_styles: {},
          table_default_attributes: {},
          image_description: true,
          image_dimensions: true,
          image_title: false,
          automatic_uploads: true,
          images_upload_handler: uploadImage,
          images_file_types: 'png,jpg,jpeg,gif,webp',
          paste_data_images: true,
          block_formats: 'Paragraph=p; Heading 2=h2; Heading 3=h3',
          content_style: 'body{font-family:inherit;font-size:15px;line-height:1.6}'
            + 'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px}img{max-width:100%;height:auto}',
          // Content creators are trusted, but keep the output conservative.
          valid_elements: RICH_TEXT_VALID_ELEMENTS,
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
