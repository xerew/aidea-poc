// What formatting rich text may carry — the single allow-list shared by the
// TinyMCE editor and the learner view (spec 2026-11-03 rich-text formatting).
// Only these exact values survive; any other declaration is removed.

export const TEXT_COLORS = [
  { name: 'Dark', hex: '#111827' },
  { name: 'Grey', hex: '#4b5563' },
  { name: 'AIDEA blue', hex: '#023e7c' },
  { name: 'Blue', hex: '#1d4ed8' },
  { name: 'Teal', hex: '#0f766e' },
  { name: 'Green', hex: '#15803d' },
  { name: 'Orange', hex: '#b45309' },
  { name: 'Red', hex: '#b91c1c' },
  { name: 'Pink', hex: '#be185d' },
  { name: 'Purple', hex: '#7e22ce' },
]

export const HIGHLIGHTS = [
  { name: 'Yellow', hex: '#fef08a' },
  { name: 'Green', hex: '#bbf7d0' },
  { name: 'Blue', hex: '#bfdbfe' },
  { name: 'Pink', hex: '#fbcfe8' },
]

export const CELL_BACKGROUNDS = [...HIGHLIGHTS, { name: 'Light grey', hex: '#f1f5f9' }]

// Every font except Lexend includes Greek; Greek in Lexend falls back to Noto Sans.
export const FONTS = [
  { name: 'Lexend', css: "Lexend, 'Noto Sans', system-ui, sans-serif" },
  { name: 'Inter', css: 'Inter, sans-serif' },
  { name: 'Open Sans', css: "'Open Sans', sans-serif" },
  { name: 'Roboto', css: 'Roboto, sans-serif' },
  { name: 'Noto Sans', css: "'Noto Sans', sans-serif" },
  { name: 'Noto Serif', css: "'Noto Serif', serif" },
  { name: 'Literata', css: 'Literata, serif' },
  { name: 'Fira Code', css: "'Fira Code', monospace" },
]

// No spaces in names: TinyMCE splits font_size_formats on spaces.
export const FONT_SIZES = [
  { name: 'Small', value: '0.875em' },
  { name: 'Normal', value: '1em' },
  { name: 'Large', value: '1.25em' },
  { name: 'Extra-large', value: '1.5em' },
  { name: 'Huge', value: '2em' },
]

export const LINE_HEIGHTS = ['1', '1.15', '1.5', '2']

export const PARAGRAPH_SPACING = [
  { name: 'Small', value: '0.25em' },
  { name: 'Normal', value: '0.5em' },
  { name: 'Large', value: '1em' },
]

export const INDENTS = ['2em', '4em', '6em', '8em', '10em']

export const TABLE_CLASSES = ['rt-striped', 'rt-borderless', 'rt-pad-compact', 'rt-pad-roomy']

// ── value parsing ──────────────────────────────────────────────────────────

/** '#rgb' | '#rrggbb' | 'rgb(r, g, b)' | 'rgba(r, g, b, a>0)' → '#rrggbb', else null. */
function parseColor(value) {
  const v = String(value ?? '').trim().toLowerCase()
  let m = v.match(/^#([0-9a-f]{3})$/)
  if (m) return `#${[...m[1]].map((c) => c + c).join('')}`
  m = v.match(/^#([0-9a-f]{6})$/)
  if (m) return `#${m[1]}`
  m = v.match(/^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)$/)
  if (m) {
    if (m[4] !== undefined && Number(m[4]) === 0) return null
    const parts = m.slice(1, 4).map(Number)
    if (parts.some((n) => n > 255)) return null
    return `#${parts.map((n) => n.toString(16).padStart(2, '0')).join('')}`
  }
  return null
}

const normFont = (v) => String(v ?? '').toLowerCase().replace(/["']/g, '').replace(/\s*,\s*/g, ',').replace(/\s+/g, ' ').trim()
const firstFamily = (v) => normFont(v).split(',')[0]

function fromList(list) {
  const allowed = new Set(list.map((x) => x.toLowerCase()))
  return (v) => (allowed.has(v.toLowerCase()) ? v.toLowerCase() : null)
}

function fromPalette(palette) {
  const allowed = new Set(palette.map((c) => c.hex))
  return (v) => {
    const hex = parseColor(v)
    return hex && allowed.has(hex) ? hex : null
  }
}

function percentage(v) {
  const m = v.trim().match(/^(\d{1,3}(?:\.\d+)?)%$/)
  return m && Number(m[1]) > 0 && Number(m[1]) <= 100 ? `${m[1]}%` : null
}

function fontFamily(v) {
  const font = FONTS.find((f) => normFont(f.css) === normFont(v))
  return font ? font.css : null
}

const ALIGN = fromList(['left', 'center', 'right', 'justify'])
const BLOCK_RULES = {
  'text-align': ALIGN,
  'line-height': fromList(LINE_HEIGHTS),
  'margin-top': fromList(PARAGRAPH_SPACING.map((s) => s.value)),
  'margin-bottom': fromList(PARAGRAPH_SPACING.map((s) => s.value)),
  'padding-left': fromList(INDENTS),
}
const CELL_RULES = {
  'text-align': ALIGN,
  'vertical-align': fromList(['top', 'middle', 'bottom']),
  'background-color': fromPalette(CELL_BACKGROUNDS),
  width: percentage,
}
const RULES = {
  span: {
    color: fromPalette(TEXT_COLORS),
    'background-color': fromPalette(HIGHLIGHTS),
    'font-family': fontFamily,
    'font-size': fromList(FONT_SIZES.map((s) => s.value)),
  },
  p: BLOCK_RULES, h2: BLOCK_RULES, h3: BLOCK_RULES, li: BLOCK_RULES, blockquote: BLOCK_RULES,
  table: { width: percentage, 'border-collapse': fromList(['collapse']) },
  col: { width: percentage },
  td: CELL_RULES, th: CELL_RULES,
}

function declarations(style) {
  const out = []
  for (const part of String(style ?? '').split(';')) {
    const i = part.indexOf(':')
    if (i < 0) continue
    const prop = part.slice(0, i).trim().toLowerCase()
    const value = part.slice(i + 1).trim()
    if (prop && value) out.push([prop, value])
  }
  return out
}

const serialise = (decls) => decls.map(([p, v]) => `${p}: ${v}`).join('; ')

/** The allowed declarations of `style` for element `tag`, re-serialised; '' when none. */
export function filterStyle(style, tag) {
  const rules = RULES[String(tag ?? '').toLowerCase()]
  if (!rules) return ''
  const kept = new Map()
  for (const [prop, value] of declarations(style)) {
    const check = rules[prop]
    // Anything with a function call other than a colour (url(), expression(), var()…) is out.
    if (!check || (value.includes('(') && !/^rgba?\(/i.test(value))) continue
    const clean = check(value)
    if (clean !== null) kept.set(prop, clean)
  }
  return serialise([...kept])
}

/** Table preset classes (tables only). */
export function filterClass(className, tag) {
  if (String(tag ?? '').toLowerCase() !== 'table') return ''
  const wanted = String(className ?? '').split(/\s+/)
  return TABLE_CLASSES.filter((c) => wanted.includes(c)).join(' ')
}

// ── colour snapping (CIE76 in Lab) ─────────────────────────────────────────

function toLab(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  const x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
  const y = r * 0.2126 + g * 0.7152 + b * 0.0722
  const z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116)
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))]
}

/** The palette hex perceptually closest to `color`, or null if `color` isn't one. */
export function nearestColor(color, palette) {
  const hex = parseColor(color)
  if (!hex) return null
  const target = toLab(hex)
  let best = null
  let bestDistance = Infinity
  for (const c of palette) {
    const lab = toLab(c.hex)
    const d = Math.hypot(lab[0] - target[0], lab[1] - target[1], lab[2] - target[2])
    if (d < bestDistance) [best, bestDistance] = [c.hex, d]
  }
  return best
}

/** Pasted formatting: colours snap to the palette, known fonts map to their
 *  stack, everything else goes through filterStyle (so unknown fonts and sizes drop). */
export function cleanPastedStyle(style, tag) {
  const t = String(tag ?? '').toLowerCase()
  const decls = []
  for (const [prop, value] of declarations(style)) {
    if (prop === 'color') {
      const hex = nearestColor(value, TEXT_COLORS)
      if (hex) decls.push([prop, hex])
    } else if (prop === 'background-color') {
      const hex = nearestColor(value, t === 'td' || t === 'th' ? CELL_BACKGROUNDS : HIGHLIGHTS)
      if (hex) decls.push([prop, hex])
    } else if (prop === 'font-family') {
      const font = FONTS.find((f) => firstFamily(f.css) === firstFamily(value))
      if (font) decls.push([prop, font.css])
    } else {
      decls.push([prop, value])
    }
  }
  return filterStyle(serialise(decls), t)
}

// ── TinyMCE init keys ──────────────────────────────────────────────────────

const flatColorMap = (palette) => palette.flatMap((c) => [c.hex.slice(1), c.name])

export function tinymceFormats() {
  return {
    font_family_formats: FONTS.map((f) => `${f.name}=${f.css}`).join(';'),
    font_size_formats: FONT_SIZES.map((s) => `${s.name}=${s.value}`).join(' '),
    line_height_formats: LINE_HEIGHTS.join(' '),
    color_map_foreground: flatColorMap(TEXT_COLORS),
    color_map_background: flatColorMap(HIGHLIGHTS),
    table_background_color_map: CELL_BACKGROUNDS.map((c) => ({ title: c.name, value: c.hex })),
    custom_colors: false,
  }
}
