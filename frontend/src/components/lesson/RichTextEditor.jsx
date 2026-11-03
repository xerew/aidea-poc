import PropTypes from 'prop-types'
import { Editor } from '@tinymce/tinymce-react'
import client from '../../api/client'
import { EDITOR_URL_OPTIONS, RICH_TEXT_VALID_ELEMENTS, makeImageUploader } from '../../lib/richText'
import { tinymceFormats, cleanPastedStyle } from '../../lib/richTextStyles'
import { EDITOR_TOOLBAR, PARAGRAPH_FORMATS, TABLE_TOOLBAR, cleanNodeStyles, setupEditor } from '../../lib/editorSetup'
// The learner-view stylesheet (fonts included), injected into the editor frame
// so authors see exactly what learners will see.
import richContentCss from '../../styles/richContent.css?inline'
import './RichTextEditor.css'

const uploadImage = makeImageUploader(client)

/**
 * Self-hosted TinyMCE editor for lesson text content. Emits HTML.
 * Assets are served from /tinymce (copied by vite-plugin-static-copy), so no
 * cloud API key is required — we run under the GPL license.
 * What formatting is allowed: lib/richTextStyles.js (spec 2026-11-03).
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
          height: 360,
          placeholder,
          ...EDITOR_URL_OPTIONS,
          plugins: 'lists link autolink table image',
          toolbar: EDITOR_TOOLBAR,
          toolbar_mode: 'wrap',
          table_toolbar: TABLE_TOOLBAR,
          ...tinymceFormats(),
          formats: PARAGRAPH_FORMATS(),
          indentation: '2em',
          indent_use_margin: false,
          table_sizing_mode: 'relative',
          table_use_colgroups: true,
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
          // Pasted formatting: colours snap to the palette, listed fonts kept, the rest dropped.
          paste_postprocess: (_editor, args) => cleanNodeStyles(args.node, cleanPastedStyle),
          block_formats: 'Paragraph=p; Heading 2=h2; Heading 3=h3',
          body_class: 'rich-html',
          content_style: `${richContentCss}\nbody{margin:1rem;font-size:15px}`,
          // Content creators are trusted, but keep the output conservative.
          valid_elements: RICH_TEXT_VALID_ELEMENTS,
          setup: setupEditor,
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
