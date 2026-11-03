// TinyMCE wiring for the rich-text editor (spec 2026-11-03): toolbar, the
// custom paragraph-spacing and table-preset buttons, and the allow-list
// applied to everything the editor loads, pastes or saves.
import { EDITOR_URL_OPTIONS, RICH_TEXT_VALID_ELEMENTS } from './richText.js'
import {
  INDENTS, PARAGRAPH_SPACING, TABLE_CLASSES, cleanPastedStyle, filterClass, filterStyle, tinymceFormats,
} from './richTextStyles.js'

export const EDITOR_TOOLBAR = [
  'undo redo',
  'blocks fontfamily fontsize',
  'bold italic underline forecolor backcolor',
  'alignleft aligncenter alignright alignjustify',
  'lineheight paragraphspacing',
  'bullist numlist outdent indent',
  'link image table',
  'removeformat',
].join(' | ')

export const TABLE_TOOLBAR = [
  'tableprops tabledelete',
  'tableinsertrowbefore tableinsertrowafter tabledeleterow',
  'tableinsertcolbefore tableinsertcolafter tabledeletecol',
  'tablemergecells tablesplitcells',
  'tablerowheader tablecolheader',
  'tablecellbackgroundcolor tablecellvalign',
  'tablestriped tableborderless tablepadding',
].join(' | ')

const BLOCKS = 'p,h2,h3,li,blockquote'

/** TinyMCE `formats`: spaceBefore{Small,Normal,Large} / spaceAfter{…}. */
export function PARAGRAPH_FORMATS() {
  const formats = {}
  for (const step of PARAGRAPH_SPACING) {
    formats[`spaceBefore${step.name}`] = { selector: BLOCKS, styles: { marginTop: step.value } }
    formats[`spaceAfter${step.name}`] = { selector: BLOCKS, styles: { marginBottom: step.value } }
  }
  return formats
}

/** Rewrite `style` (through `clean(style, tag)`) and `class` (table presets
 *  only) on `node` and every element inside it; drop attributes left empty. */
export function cleanNodeStyles(node, clean) {
  for (const el of [node, ...node.querySelectorAll('*')]) {
    const tag = el.nodeName.toLowerCase()
    for (const [attr, filter] of [['style', clean], ['class', filterClass]]) {
      if (!el.hasAttribute(attr)) continue
      const value = filter(el.getAttribute(attr), tag)
      if (value) el.setAttribute(attr, value)
      else el.removeAttribute(attr)
    }
  }
}

// Applied to TinyMCE's own node tree (parser: load, setContent, paste;
// serializer: what gets saved), so the editor never keeps what display drops.
function addAllowListFilters(target) {
  target.addAttributeFilter('style', (nodes) => {
    for (const n of nodes) {
      const clean = filterStyle(n.attr('style'), n.name) || null
      n.attr('style', clean)
      if (n.attr('data-mce-style') !== undefined) n.attr('data-mce-style', clean)
    }
  })
  target.addAttributeFilter('data-mce-style', (nodes) => {
    for (const n of nodes) n.attr('data-mce-style', filterStyle(n.attr('data-mce-style'), n.name) || null)
  })
  target.addAttributeFilter('class', (nodes) => {
    for (const n of nodes) n.attr('class', filterClass(n.attr('class'), n.name) || null)
  })
}

const PADDING = [
  { text: 'Compact', cls: 'rt-pad-compact' },
  { text: 'Normal', cls: null },
  { text: 'Roomy', cls: 'rt-pad-roomy' },
]

/** TinyMCE `setup(editor)`: allow-list filters and the custom buttons. */
const MAX_INDENT_EM = parseFloat(INDENTS[INDENTS.length - 1])

export function setupEditor(editor) {
  editor.on('PreInit', () => {
    addAllowListFilters(editor.parser)
    addAllowListFilters(editor.serializer)
  })

  // Indent stops at the last allowed step (a deeper one would vanish on save).
  editor.on('BeforeExecCommand', (e) => {
    if (e.command !== 'Indent') return
    const blocks = editor.selection.getSelectedBlocks()
    if (blocks.length && blocks.every((b) => parseFloat(editor.dom.getStyle(b, 'padding-left')) >= MAX_INDENT_EM)) {
      e.preventDefault()
    }
  })

  const spacingItems = (direction, label) => [
    ...PARAGRAPH_SPACING.map((step) => ({
      type: 'menuitem',
      text: `${label}: ${step.name}`,
      onAction: () => {
        editor.undoManager.transact(() => {
          for (const s of PARAGRAPH_SPACING) editor.formatter.remove(`${direction}${s.name}`)
          editor.formatter.apply(`${direction}${step.name}`)
        })
      },
    })),
    {
      type: 'menuitem',
      text: `${label}: Default`,
      onAction: () => editor.undoManager.transact(() => {
        for (const s of PARAGRAPH_SPACING) editor.formatter.remove(`${direction}${s.name}`)
      }),
    },
  ]
  editor.ui.registry.addMenuButton('paragraphspacing', {
    text: 'Spacing',
    tooltip: 'Space before / after paragraph',
    fetch: (callback) => callback([
      ...spacingItems('spaceBefore', 'Space before'),
      { type: 'separator' },
      ...spacingItems('spaceAfter', 'Space after'),
    ]),
  })

  const currentTable = () => editor.dom.getParent(editor.selection.getNode(), 'table')
  const setTableClass = (add, remove = []) => {
    const table = currentTable()
    if (!table) return
    editor.undoManager.transact(() => {
      for (const cls of remove) editor.dom.removeClass(table, cls)
      if (add) editor.dom.addClass(table, add)
    })
    editor.nodeChanged()
  }
  const toggleButton = (name, text, cls) => editor.ui.registry.addToggleButton(name, {
    text,
    tooltip: text,
    onAction: () => {
      const table = currentTable()
      if (table) setTableClass(editor.dom.hasClass(table, cls) ? null : cls, [cls])
    },
    onSetup: (api) => {
      const sync = () => {
        const table = currentTable()
        api.setActive(!!table && editor.dom.hasClass(table, cls))
      }
      editor.on('NodeChange', sync)
      return () => editor.off('NodeChange', sync)
    },
  })
  toggleButton('tablestriped', 'Striped rows', 'rt-striped')
  toggleButton('tableborderless', 'No borders', 'rt-borderless')

  const paddingClasses = TABLE_CLASSES.filter((c) => c.startsWith('rt-pad-'))
  editor.ui.registry.addMenuButton('tablepadding', {
    text: 'Cell padding',
    tooltip: 'Cell padding',
    fetch: (callback) => callback(PADDING.map((p) => ({
      type: 'menuitem',
      text: p.text,
      onAction: () => setTableClass(p.cls, paddingClasses),
    }))),
  })
}

/** The TinyMCE `init` options (everything except script path and licence), so
 *  the component and the real-editor tests run the same configuration. */
export function editorInit({ placeholder = '', uploadImage = undefined, contentStyle = '' } = {}) {
  return {
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
    // Underline as <u> (TinyMCE's default is a styled span, which the allow-list drops).
    formats: { ...PARAGRAPH_FORMATS(), underline: { inline: 'u', exact: true } },
    indentation: '2em',
    indent_use_margin: false,
    table_sizing_mode: 'relative',
    table_use_colgroups: true,
    // "Header row" makes <th> cells (the default keeps <td> in <thead>, which looks unchanged).
    table_header_type: 'sectionCells',
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
    // Chrome/Edge/Safari: keep pasted styles so paste_postprocess can clean them
    // (TinyMCE's default strips every style before it runs).
    paste_webkit_styles: 'all',
    // Pasted formatting: colours snap to the palette, listed fonts kept, the rest dropped.
    paste_postprocess: (_editor, args) => cleanNodeStyles(args.node, cleanPastedStyle),
    block_formats: 'Paragraph=p; Heading 2=h2; Heading 3=h3',
    body_class: 'rich-html',
    content_style: contentStyle,
    // Content creators are trusted, but keep the output conservative.
    valid_elements: RICH_TEXT_VALID_ELEMENTS,
    setup: setupEditor,
  }
}
