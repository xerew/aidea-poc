// TinyMCE wiring for the rich-text editor (spec 2026-11-03): toolbar, the
// custom paragraph-spacing and table-preset buttons, and the allow-list
// applied to everything the editor loads, pastes or saves.
import { PARAGRAPH_SPACING, TABLE_CLASSES, filterClass, filterStyle } from './richTextStyles.js'

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
    for (const n of nodes) n.attr('style', filterStyle(n.attr('style'), n.name) || null)
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
export function setupEditor(editor) {
  editor.on('PreInit', () => {
    addAllowListFilters(editor.parser)
    addAllowListFilters(editor.serializer)
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
