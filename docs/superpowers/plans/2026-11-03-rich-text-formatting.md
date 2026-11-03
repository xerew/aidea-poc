# Rich-text Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Authors get fonts, named sizes, palette colours and highlights, paragraph alignment, spacing and indent, and table formatting in the text editor. Learners see exactly that, safely. Tables fill the page, and all fonts are self-hosted.

**Architecture:**
- **One allow-list.** A pure module `frontend/src/lib/richTextStyles.js` holds the palette, fonts, steps, the declaration filter and the paste snapping.
- **Display.** A DOMPurify instance built by `frontend/src/lib/sanitizeRichHtml.js` enforces the allow-list and wraps tables in a scroll container.
- **Editor.** TinyMCE takes its formats from the same module and runs the same filter on everything it parses.
- **Fonts and styles.** One stylesheet `frontend/src/styles/richContent.css` (fonts plus `.rich-html` rules) serves the learner view and, via `?inline`, the editor frame.
- **Translation.** The backend gains one retry with styled spans unwrapped before the plain-text fallback.

**Tech Stack:** React 19, TinyMCE 8 (GPL core plugins only), DOMPurify 3, `@fontsource/*`, jsdom (new devDependency, tests only), Django/lxml.

**Spec:** `docs/superpowers/specs/2026-11-03-rich-text-formatting-design.md`

## Global Constraints

- **Storage:** inline `style` attributes. Allowed values only:
  - palette colours;
  - size steps;
  - listed fonts;
  - fixed spacing, line-height and indent steps;
  - alignment keywords;
  - column/table widths as percentages ≤ 100%.
- **Table-level presets** (striped rows, borderless, padding) are a fixed set of classes on `<table>`, because striping can't be expressed as an inline style. `class` is allowed only there, and only these values.
- **Filtering:** anything else is removed, both in the editor and at display. Old content renders as before, except that tables now fill the width.
- **Fonts:** self-hosted only. No request to `fonts.googleapis.com` / `fonts.gstatic.com` anywhere.
  - The default stack is `Lexend → Noto Sans → system-ui → sans-serif`.
  - The picker fonts all include Greek.
- **TinyMCE:** GPL core only. The interface stays English, so no new platform locale strings.
- **Runner:**
  - backend from `backend/`: `UV="/c/Users/Nikos A. Grammatikos/.local/bin/uv.exe"`, then `"$UV" run manage.py test …` and `"$UV" run ruff check hub analytics`;
  - frontend from `frontend/`: `npm test`, `npm run lint`, `VITE_API_URL=http://localhost:8000/api npm run build`.
- **Git:** keep each file's line endings. Commit and push per task on `master`, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Exact values (pinned here; tests use them)

| Name | Values |
|---|---|
| `TEXT_COLORS` | Dark `#111827`, Grey `#4b5563`, AIDEA blue `#023e7c`, Blue `#1d4ed8`, Teal `#0f766e`, Green `#15803d`, Orange `#b45309`, Red `#b91c1c`, Pink `#be185d`, Purple `#7e22ce` |
| `HIGHLIGHTS` | Yellow `#fef08a`, Green `#bbf7d0`, Blue `#bfdbfe`, Pink `#fbcfe8` |
| `CELL_BACKGROUNDS` | the 4 highlights + Light grey `#f1f5f9` |
| `FONTS` (name → CSS stack) | Lexend → `Lexend, 'Noto Sans', system-ui, sans-serif`; Inter → `Inter, sans-serif`; Open Sans → `'Open Sans', sans-serif`; Roboto → `Roboto, sans-serif`; Noto Sans → `'Noto Sans', sans-serif`; Noto Serif → `'Noto Serif', serif`; Literata → `Literata, serif`; Fira Code → `'Fira Code', monospace` |
| `FONT_SIZES` | Small `0.875em`, Normal `1em`, Large `1.25em`, Extra-large `1.5em`, Huge `2em` (no spaces in names: TinyMCE splits `font_size_formats` on spaces) |
| `LINE_HEIGHTS` | `1`, `1.15`, `1.5`, `2` |
| `PARAGRAPH_SPACING` | Small `0.25em`, Normal `0.5em`, Large `1em` (for `margin-top` / `margin-bottom`) |
| `INDENTS` | `padding-left`: `2em`, `4em`, `6em`, `8em`, `10em` |
| `TABLE_CLASSES` | `rt-striped`, `rt-borderless`, `rt-pad-compact`, `rt-pad-roomy` |

**Allowed declarations per tag:**
- `span`: `color` ∈ TEXT_COLORS, `background-color` ∈ HIGHLIGHTS, `font-family` ∈ FONTS stacks, `font-size` ∈ FONT_SIZES.
- `p`, `h2`, `h3`, `li`, `blockquote`:
  - `text-align` ∈ {left, center, right, justify};
  - `line-height` ∈ LINE_HEIGHTS;
  - `margin-top` / `margin-bottom` ∈ PARAGRAPH_SPACING;
  - `padding-left` ∈ INDENTS.
- `table`: `width` (percentage ≤ 100), `border-collapse: collapse`.
- `col`: `width` (percentage ≤ 100).
- `td`, `th`:
  - `text-align`;
  - `vertical-align` ∈ {top, middle, bottom};
  - `background-color` ∈ CELL_BACKGROUNDS;
  - `width` (percentage ≤ 100).

**Value matching:**
- Values compare case-insensitively.
- Colours match by normalised hex (`#rgb`, `#rrggbb` or `rgb(r, g, b)`).
- Font stacks match after lowercasing, removing quotes and collapsing spaces.

## Review Focus

1. **Pasted or hand-edited HTML never reaches learners** with a style or class outside the allow-list. Examples:
   - `position: fixed`, `background-image: url(...)`, `expression(...)`, `behavior`;
   - `display: none`, `font-size: 200px`;
   - an off-palette `color`;
   - `class` on a non-table element.
   - Pinned by Task 2 `sanitizer strips every disallowed style and class`.
2. **Existing content (no styles, plain tables) renders the same as before,** apart from the table wrapper. Pinned by Task 2 `legacy content passes through unchanged apart from the table wrapper`.
3. **A wide table on a phone scrolls inside its own wrapper,** and the page never scrolls sideways. Pinned by Task 2 (the wrapper exists) and Task 3 `rich content CSS: tables fill the width and scroll inside their wrapper`.
4. **Greek text in the default font renders in Noto Sans,** not a random device font. Pinned by Task 3 `fonts are self-hosted and the default stack falls back to Noto Sans for Greek`.
5. **A translated block whose model answer drops a styled span** still gets translated text, keeps its bold and links, and keeps its own paragraph style. Pinned by Task 5 `test_styled_span_dropped_by_model_keeps_text_bold_and_block_style`.

---

### Task 1: Style allow-list module

**Files:**
- Create: `frontend/src/lib/richTextStyles.js`, `frontend/src/lib/richTextStyles.test.js`

**Interfaces — Produces** (all exported from `richTextStyles.js`):
- **Constants:** `TEXT_COLORS`, `HIGHLIGHTS`, `CELL_BACKGROUNDS` (arrays of `{name, hex}`); `FONTS` (`{name, css}`); `FONT_SIZES` (`{name, value}`); `LINE_HEIGHTS` (string[]); `PARAGRAPH_SPACING` (`{name, value}`); `INDENTS` (string[]); `TABLE_CLASSES` (string[]).
- **`filterStyle(style: string, tag: string) -> string`:** the allowed declarations, re-serialised as `prop: value; prop: value`, or `''`.
- **`filterClass(className: string, tag: string) -> string`:** for `table`, the subset of TABLE_CLASSES; otherwise `''`.
- **`nearestColor(color: string, palette: {hex}[]) -> string | null`:**
  - accepts `#rgb`, `#rrggbb`, `rgb(…)` or `rgba(…)`;
  - returns the palette hex with the smallest CIE76 distance (sRGB → Lab);
  - returns null if the input is unparseable or transparent.
- **`cleanPastedStyle(style: string, tag: string) -> string`:**
  - snaps `color` to TEXT_COLORS;
  - snaps `background-color` to HIGHLIGHTS on `span`, or to CELL_BACKGROUNDS on `td`/`th`;
  - maps `font-family` to the listed font whose first family name matches the pasted first family, else drops it;
  - then runs `filterStyle`.
- **`tinymceFormats() -> object`:** the TinyMCE init keys built from the constants:
  - `font_family_formats` (`Name=stack;…`);
  - `font_size_formats` (`Name=value …`);
  - `line_height_formats`;
  - `color_map_foreground` / `color_map_background` / `table_background_color_map`;
  - `custom_colors: false`.

- [ ] **Step 1: Write the failing tests.** `richTextStyles.test.js`. Name the test for each behaviour and assert:

```js
test('text colours are readable on white and highlights keep black text readable', () => {
  for (const c of TEXT_COLORS) assert.ok(contrast(c.hex, '#ffffff') >= 4.5, c.name)
  for (const c of [...HIGHLIGHTS, ...CELL_BACKGROUNDS]) assert.ok(contrast('#000000', c.hex) >= 4.5, c.name)
})
// contrast(): WCAG relative-luminance ratio, written in the test file.

test('filterStyle keeps exactly the allowed declarations per tag', () => {
  assert.equal(filterStyle('color: #B91C1C; font-size: 1.25em; font-family: "Open Sans", sans-serif', 'span'),
    "color: #b91c1c; font-size: 1.25em; font-family: 'Open Sans', sans-serif")
  assert.equal(filterStyle('text-align: justify; line-height: 1.5; margin-top: 1em; padding-left: 4em', 'p'),
    'text-align: justify; line-height: 1.5; margin-top: 1em; padding-left: 4em')
  assert.equal(filterStyle('vertical-align: middle; background-color: #f1f5f9; width: 33.33%', 'td'),
    'vertical-align: middle; background-color: #f1f5f9; width: 33.33%')
  assert.equal(filterStyle('width: 100%; border-collapse: collapse; border-width: 1px', 'table'),
    'width: 100%; border-collapse: collapse')
})

test('filterStyle drops everything else', () => {
  for (const [style, tag] of [
    ['color: #ff0000', 'span'], ['position: fixed; top: 0', 'p'], ['background-image: url(https://x/y.png)', 'td'],
    ['width: expression(alert(1))', 'td'], ['behavior: url(x.htc)', 'span'], ['display: none', 'p'],
    ['font-size: 200px', 'span'], ['font-family: Comic Sans MS', 'span'], ['padding-left: 40em', 'p'],
    ['width: 120%', 'col'], ['color: #b91c1c', 'p'], ['text-align: left', 'span'], ['color: #b91c1c', 'div'],
  ]) assert.equal(filterStyle(style, tag), '', `${tag} ${style}`)
})

test('table classes only on tables, only the presets', () => {
  assert.equal(filterClass('rt-striped evil rt-pad-roomy', 'table'), 'rt-striped rt-pad-roomy')
  assert.equal(filterClass('rt-striped', 'p'), '')
})

test('nearestColor snaps to the palette', () => {
  assert.equal(nearestColor('#000000', TEXT_COLORS), '#111827')
  assert.equal(nearestColor('#b91c1d', TEXT_COLORS), '#b91c1c')
  assert.equal(nearestColor('rgb(29, 78, 216)', TEXT_COLORS), '#1d4ed8')
  assert.equal(nearestColor('#ffff00', HIGHLIGHTS), '#fef08a')
  assert.equal(nearestColor('transparent', TEXT_COLORS), null)
})

test('pasted styles are snapped, mapped or dropped', () => {
  assert.equal(cleanPastedStyle('color: rgb(0, 0, 0); font-family: Roboto, Arial; font-size: 11pt', 'span'),
    'color: #111827; font-family: Roboto, sans-serif')
  assert.equal(cleanPastedStyle('font-family: Calibri, sans-serif; background-color: #ffff00', 'span'),
    'background-color: #fef08a')
  assert.equal(cleanPastedStyle('background-color: #eeeeee', 'td'), 'background-color: #f1f5f9')
})

test('TinyMCE formats come from the same constants', () => {
  const f = tinymceFormats()
  assert.ok(f.font_size_formats.includes('Extra-large=1.5em'))
  assert.ok(f.font_family_formats.startsWith("Lexend=Lexend, 'Noto Sans', system-ui, sans-serif;"))
  assert.equal(f.line_height_formats, '1 1.15 1.5 2')
  assert.equal(f.custom_colors, false)
  assert.deepEqual(f.color_map_foreground.slice(0, 2), ['111827', 'Dark'])
  assert.equal(f.table_background_color_map.length, 5)
})
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `npm test` (from `frontend/`).
  - Expected: `ERR_MODULE_NOT_FOUND` for `richTextStyles.js`.

- [ ] **Step 3: Implement `richTextStyles.js`** with the exports above and the pinned values.
  - Parse declarations by splitting on `;` and the first `:`.
  - Reject any value containing `(`, except a colour `rgb(`/`rgba(` that normalises to hex.
  - `color_map_*` follows TinyMCE's flat `[hexWithoutHash, name, …]` format; `table_background_color_map` is `[{title, value}]`.

- [ ] **Step 4: Run the tests to verify they pass.**
  - Run: `npm test`.
  - Expected: all pass.

- [ ] **Step 5: Commit** `feat: rich-text style allow-list (palette, fonts, steps, paste snapping)`.

---

### Task 2: Display sanitizer and table wrapper

**Files:**
- Create: `frontend/src/lib/sanitizeRichHtml.js`, `frontend/src/lib/sanitizeRichHtml.test.js`
- Modify:
  - `frontend/src/lib/richText.js` (allow-list);
  - `frontend/src/lib/richText.test.js` (the old "no style" assertion becomes the new rule);
  - `frontend/src/components/lesson/HtmlContent.jsx`;
  - `frontend/package.json` (devDependency `jsdom`).

**Interfaces:**
- **Consumes:** Task 1 `filterStyle`, `filterClass`.
- **Produces:**
  - `createRichHtmlSanitizer(win: Window) -> (html: string) => string`. A DOMPurify instance bound to `win`, with the image-src hook (moved from `HtmlContent`) and the style/class hooks. It wraps every `table` in `<div class="rich-table-scroll">`.
  - `richText.js`: `RICH_TEXT_VALID_ELEMENTS` adds `span[style]`, `colgroup`, `col[style]`, and `[style]` on `p`, `h2`, `h3`, `li`, `blockquote`, `table`, `td`, `th`, plus `table[class]`. `SANITIZE_CONFIG` adds tags `span`, `colgroup`, `col` and attributes `style`, `class`.

- [ ] **Step 1: Install the test DOM.** Run `npm i -D jsdom` (from `frontend/`).

- [ ] **Step 2: Write the failing tests.** `sanitizeRichHtml.test.js`, with `const clean = createRichHtmlSanitizer(new JSDOM('').window)` at the top:

```js
test('sanitizer strips every disallowed style and class', () => {
  const out = clean('<p style="position: fixed; text-align: center" class="x">A</p>'
    + '<span style="color: #ff0000; background-image: url(https://e/x.png)">B</span>'
    + '<td style="width: expression(alert(1))">C</td><span style="display:none">D</span>')
  assert.ok(!/position|url\(|expression|display|class="x"|#ff0000/i.test(out), out)
  assert.ok(out.includes('<p style="text-align: center">A</p>'), out)
  assert.ok(out.includes('<span>B</span>') || out.includes('B'), out)
})

test('allowed formatting reaches the learner unchanged', () => {
  const html = '<p style="line-height: 1.5; padding-left: 2em"><span style="color: #15803d; font-size: 1.25em">x</span></p>'
    + '<table class="rt-striped" style="width: 100%"><colgroup><col style="width: 30%"><col style="width: 70%"></colgroup>'
    + '<tbody><tr><th style="background-color: #f1f5f9">h</th><td style="vertical-align: top">c</td></tr></tbody></table>'
  const out = clean(html)
  for (const piece of ['line-height: 1.5', 'color: #15803d', 'class="rt-striped"', '<col style="width: 30%">',
    'background-color: #f1f5f9', 'vertical-align: top']) assert.ok(out.includes(piece), piece)
})

test('legacy content passes through unchanged apart from the table wrapper', () => {
  const legacy = '<p><strong>Hi</strong> <a href="https://x.org" target="_blank" rel="noopener">link</a></p>'
    + '<table><tbody><tr><td>a</td></tr></tbody></table>'
  assert.equal(clean(legacy), '<p><strong>Hi</strong> <a href="https://x.org" target="_blank" rel="noopener">link</a></p>'
    + '<div class="rich-table-scroll"><table><tbody><tr><td>a</td></tr></tbody></table></div>')
})

test('image rules still apply', () => {
  assert.ok(!clean('<img src="http://evil.example/a.png">').includes('<img'))
  assert.ok(clean('<img src="/media/a.png" alt="a">').includes('src="/media/a.png"'))
})
```

  In `richText.test.js`, replace `assert.ok(!SANITIZE_CONFIG.ALLOWED_ATTR.includes('style'))` with assertions that `style`, `class`, `span`, `colgroup` and `col` are allowed, while `script`, `iframe` and `style` (as a tag) are not.

- [ ] **Step 3: Run the tests to verify they fail.**
  - Run: `npm test`.
  - Expected: `ERR_MODULE_NOT_FOUND` for `sanitizeRichHtml.js`, and the `richText` assertions fail.

- [ ] **Step 4: Implement.**
  - `createRichHtmlSanitizer(win)`:
    - `DOMPurify(win)`;
    - `uponSanitizeElement` handles the image-src rule;
    - `uponSanitizeAttribute`: for `style`, `data.attrValue = filterStyle(...)`; for `class`, `filterClass(...)`; set `data.keepAttr = false` when the result is empty;
    - after sanitising with `RETURN_DOM_FRAGMENT`, wrap each `table` and serialise.
  - `HtmlContent.jsx`: use a module-level `const sanitize = createRichHtmlSanitizer(window)`, and drop its global `DOMPurify.addHook`.
  - Update `richText.js` as in Interfaces.

- [ ] **Step 5: Run the tests and lint.**
  - Run: `npm test` and `npm run lint`.
  - Expected: all pass, lint clean.

- [ ] **Step 6: Commit** `feat: learner view keeps only allowed formatting; tables wrapped for scrolling`.

---

### Task 3: Self-hosted fonts and the rich-content stylesheet

**Files:**
- Create:
  - `frontend/src/styles/fonts.css` (fontsource imports);
  - `frontend/src/styles/richContent.css` (`@import './fonts.css'` plus every `.rich-html` rule, moved from `components/lesson/RichTextEditor.css`);
  - `frontend/src/lib/fonts.test.js`.
- Modify:
  - `frontend/index.html` (remove the three Google lines);
  - `frontend/src/index.css` (comment line 8; `--font-sans` and the body stack become `'Lexend', 'Noto Sans', system-ui, sans-serif`);
  - `frontend/src/main.jsx` (import `./styles/fonts.css`);
  - `frontend/src/components/lesson/RichTextEditor.css` (keep only the editor chrome rule);
  - `frontend/src/components/lesson/HtmlContent.jsx` (import `../../styles/richContent.css`);
  - `frontend/package.json`.

**Interfaces:**
- **Produces:** `frontend/src/styles/richContent.css`, imported by `HtmlContent` and, as `?inline`, by the editor (Task 4).
- **Classes:** `.rich-table-scroll`, `.rt-striped`, `.rt-borderless`, `.rt-pad-compact`, `.rt-pad-roomy`.

- [ ] **Step 1: Install the fonts.**
  - Run: `npm i @fontsource/lexend @fontsource/oswald @fontsource/inter @fontsource/open-sans @fontsource/roboto @fontsource/noto-sans @fontsource/noto-serif @fontsource/literata @fontsource/fira-code`.
  - **Weights in `fonts.css`:**
    - Lexend 300/400/500/600;
    - Oswald 700;
    - picker fonts 400, 700 and 400-italic (Fira Code: 400 and 700 only, it has no italic);
    - Noto Sans 400/700.

- [ ] **Step 2: Write the failing test.** `fonts.test.js` reads the files with `fs`:

```js
test('fonts are self-hosted and the default stack falls back to Noto Sans for Greek', () => {
  const index = read('../../index.html'); const css = read('../index.css'); const fonts = read('../styles/fonts.css')
  assert.ok(!/fonts\.(googleapis|gstatic)\.com/.test(index + css + fonts))
  assert.match(css, /--font-sans:\s*'Lexend', 'Noto Sans', system-ui, sans-serif/)
  for (const pkg of ['lexend', 'oswald', 'inter', 'open-sans', 'roboto', 'noto-sans', 'noto-serif', 'literata', 'fira-code'])
    assert.ok(fonts.includes(`@fontsource/${pkg}/`), pkg)
})

test('rich content CSS: tables fill the width and scroll inside their wrapper', () => {
  const css = read('../styles/richContent.css')
  assert.match(css, /\.rich-table-scroll\s*\{[^}]*overflow-x:\s*auto/)
  assert.match(css, /\.rich-html table\s*\{[^}]*width:\s*100%/)
  assert.ok(!/\.rich-html table\s*\{[^}]*display:\s*block/.test(css))
  for (const cls of ['.rt-striped', '.rt-borderless', '.rt-pad-compact', '.rt-pad-roomy']) assert.ok(css.includes(cls), cls)
})
```

- [ ] **Step 3: Run the tests to verify they fail.**
  - Run: `npm test`.
  - Expected: both new tests fail (missing files, Google links present).

- [ ] **Step 4: Implement** the files above. In `richContent.css`:
  - **Tables:** `.rich-html table { width: 100%; border-collapse: collapse; table-layout: auto; }` plus `.rich-html td, .rich-html th { min-width: 7ch; }`.
  - **Wrapper:** `.rich-table-scroll { overflow-x: auto; margin: 0.75rem 0; }`.
  - **`.rt-striped tbody tr:nth-child(even) td`:** light grey `#f8fafc`. A cell's own background wins, because inline styles beat class rules.
  - **`.rt-borderless`:** no cell borders.
  - **Padding presets:** `.rt-pad-compact` cells `0.2rem 0.4rem`, normal `0.45rem 0.6rem` (today's), `.rt-pad-roomy` `0.75rem 1rem`.

- [ ] **Step 5: Run the tests, lint and build.**
  - Run: `npm test`, `npm run lint` and `VITE_API_URL=http://localhost:8000/api npm run build`.
  - Expected: pass. `grep -c "woff2" dist/assets/*.css` is greater than 0, and `grep -rl "fonts.googleapis" dist` returns nothing.

- [ ] **Step 6: Commit** `feat: self-hosted fonts (Greek fallback) and a shared rich-content stylesheet; tables fill the page`.

---

### Task 4: Editor toolbar, formats and filtering

**Files:**
- Create: `frontend/src/lib/editorSetup.js`, `frontend/src/lib/editorSetup.test.js`
- Modify: `frontend/src/components/lesson/RichTextEditor.jsx`

**Interfaces:**
- **Consumes:**
  - Task 1 `tinymceFormats`, `filterStyle`, `filterClass`, `cleanPastedStyle`, `PARAGRAPH_SPACING`, `TABLE_CLASSES`;
  - Task 3 `richContent.css`.
- **Produces:**
  - `EDITOR_TOOLBAR` and `TABLE_TOOLBAR` (strings);
  - `PARAGRAPH_FORMATS() -> object` (TinyMCE `formats` for `spaceBefore{Small,Normal,Large}` / `spaceAfter{…}`, selector `p,h2,h3,li,blockquote`);
  - `cleanNodeStyles(node: Element, clean: (style, tag) => string)`: walks the element and its descendants, rewrites each `style`/`class` through `clean` / `filterClass`, and removes empty attributes.

- [ ] **Step 1: Write the failing tests.** `editorSetup.test.js`, where `fragment(html)` returns a jsdom `div` whose `innerHTML` is `html`:

```js
test('toolbar offers every control the spec lists', () => {
  for (const b of ['fontfamily', 'fontsize', 'forecolor', 'backcolor', 'alignleft', 'aligncenter', 'alignright',
    'alignjustify', 'lineheight', 'paragraphspacing', 'outdent', 'indent']) assert.ok(EDITOR_TOOLBAR.includes(b), b)
  for (const b of ['tablecellbackgroundcolor', 'tablecellvalign', 'tablerowheader', 'tablecolheader',
    'tablestriped', 'tableborderless', 'tablepadding']) assert.ok(TABLE_TOOLBAR.includes(b), b)
})

test('paragraph spacing formats use the pinned steps', () => {
  const f = PARAGRAPH_FORMATS()
  assert.deepEqual(f.spaceBeforeLarge, { selector: 'p,h2,h3,li,blockquote', styles: { marginTop: '1em' } })
  assert.deepEqual(f.spaceAfterSmall.styles, { marginBottom: '0.25em' })
})

test('cleanNodeStyles applies the paste rules to a pasted fragment', () => {
  const root = fragment('<p style="text-align:center; font-family: Calibri"><span style="color: rgb(0,0,0); font-size: 11pt">x</span></p>'
    + '<table class="MsoTable rt-striped"><tbody><tr><td style="background-color:#eee">y</td></tr></tbody></table>')
  cleanNodeStyles(root, cleanPastedStyle)
  assert.equal(root.innerHTML, '<p style="text-align: center"><span style="color: #111827">x</span></p>'
    + '<table class="rt-striped"><tbody><tr><td style="background-color: #f1f5f9">y</td></tr></tbody></table>')
})
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `npm test`.
  - Expected: `ERR_MODULE_NOT_FOUND` for `editorSetup.js`.

- [ ] **Step 3: Implement `editorSetup.js`, then wire `RichTextEditor.jsx`.** Init gains:
  - `...tinymceFormats()`;
  - `toolbar: EDITOR_TOOLBAR`, `table_toolbar: TABLE_TOOLBAR`;
  - `formats: PARAGRAPH_FORMATS()`;
  - `indentation: '2em'`, `indent_use_margin: false`;
  - `table_sizing_mode: 'relative'`, `table_use_colgroups: true`;
  - `table_appearance_options: false`; keep `table_advtab`, `table_cell_advtab` and `table_row_advtab` set to false (the toolbar buttons replace them);
  - `content_style: richContentCss + 'body{…}'`, where `import richContentCss from '../../styles/richContent.css?inline'`, together with `body_class: 'rich-html'`. Keep the existing `img`/`table` rules only where they don't duplicate `richContent.css`.
  - `paste_postprocess: (_, args) => cleanNodeStyles(args.node, cleanPastedStyle)`.
  - In `setup(editor)`:
    1. `editor.on('PreInit', () => editor.parser.addAttributeFilter('style,class', …))`, running `filterStyle` / `filterClass` per node, so loading, `setContent` and save all go through the allow-list.
    2. `editor.ui.registry.addMenuButton('paragraphspacing', …)` with items "Space before: Small/Normal/Large" and "Space after: …", toggling the formats.
    3. Toggle buttons `tablestriped` and `tableborderless`, plus a menu button `tablepadding` (Compact / Normal / Roomy). They toggle `TABLE_CLASSES` on `editor.dom.getParent(selection, 'table')` and fire `editor.nodeChanged()`.

- [ ] **Step 4: Run the tests, lint and build.**
  - Run: `npm test`, `npm run lint` and the build.
  - Expected: all clean.

- [ ] **Step 5: Manual check (dev server).** In a text resource:
  - the body text is in Lexend;
  - the font, size, colour (palette only, no custom picker), highlight, alignment, line height, spacing and indent controls apply;
  - a table can be given column widths, cell background, alignment, header row, striped and borderless;
  - pasting a coloured Word paragraph snaps its colour.
  - Save, then open the learner view: it looks the same.

- [ ] **Step 6: Commit** `feat: editor fonts, sizes, palette, spacing and table formatting`.

---

### Task 5: Translation keeps formatting where it can

**Files:**
- Modify: `backend/hub/html_translate.py` (`_translate_block`)
- Test: `backend/hub/tests/test_html_translate_styles.py` (new)

**Interfaces:**
- **Produces:** `_unwrap_styled_spans(root) -> None`, which replaces each `span` carrying a `style` attribute with its children and text. `_translate_block` tries: two normal attempts, then one attempt on the unwrapped fragment, then the plain fallback.

- [ ] **Step 1: Write the failing tests.**

```python
class StyledTranslationTests(SimpleTestCase):
    def test_block_and_cell_styles_survive(self):
        html = ('<p style="text-align: center; line-height: 1.5">Hello <b>world</b></p>'
                '<table class="rt-striped"><colgroup><col style="width: 30%"></colgroup>'
                '<tbody><tr><td style="background-color: #f1f5f9">Cell</td></tr></tbody></table>')
        out = translate_html(html, lambda f: f.replace('Hello', 'Γεια').replace('Cell', 'Κελί'), lambda t: t)
        for piece in ['style="text-align: center; line-height: 1.5"', 'Γεια', '<b>world</b>', 'class="rt-striped"',
                      '<col style="width: 30%">', 'style="background-color: #f1f5f9"', 'Κελί']:
            self.assertIn(piece, out)

    def test_styled_span_kept_when_the_model_keeps_it(self):
        html = '<p>Say <span style="color: #b91c1c">hi</span></p>'
        out = translate_html(html, lambda f: f.replace('Say', 'Πες'), lambda t: t)
        self.assertIn('<span style="color: #b91c1c">hi</span>', out)

    def test_styled_span_dropped_by_model_keeps_text_bold_and_block_style(self):
        html = '<p style="text-align: right"><b>Say</b> <span style="color: #b91c1c">hi</span> <a href="https://x.org">x</a></p>'
        def model(fragment):  # never returns spans
            return re.sub(r'</?span[^>]*>', '', fragment).replace('Say', 'Πες')
        out = translate_html(html, model, lambda t: 'PLAIN')
        self.assertIn('style="text-align: right"', out)
        self.assertIn('<b>Πες</b>', out)
        self.assertIn('href="https://x.org"', out)
        self.assertNotIn('PLAIN', out)
        self.assertNotIn('<span', out)
```

- [ ] **Step 2: Run the tests to verify they fail.**
  - Run: `"$UV" run manage.py test hub.tests.test_html_translate_styles -v 2`.
  - Expected: the span-dropped test fails, because today's code goes straight to the plain fallback ('PLAIN'). The other two may already pass; they pin existing behaviour.

- [ ] **Step 3: Implement** `_unwrap_styled_spans` and the extra attempt in `_translate_block`. Recompute the expected signature and the source length from the unwrapped fragment, and restore images as in the normal path.

- [ ] **Step 4: Run the tests and lint.**
  - Run: `"$UV" run manage.py test hub.tests.test_html_translate_styles hub.tests.test_html_translate hub.tests.test_html_translate_fixes` and `"$UV" run ruff check hub`.
  - Expected: all pass.

- [ ] **Step 5: Commit** `feat: a translation that drops inline formatting keeps the text, bold and links`.

---

### Task 6: Docs and full verification

- [ ] **Step 1: CLAUDE.md.** Replace the **Rich text** paragraph with:
  - the allow-list (`frontend/src/lib/richTextStyles.js`: palette, fonts, steps, per-tag declarations; table preset classes);
  - display through `createRichHtmlSanitizer` (`frontend/src/lib/sanitizeRichHtml.js`);
  - the shared stylesheet `frontend/src/styles/richContent.css`, also injected into the editor;
  - self-hosted fonts in `frontend/src/styles/fonts.css`, with no Google Fonts;
  - the translation fallback order (normal ×2 → spans unwrapped → plain).

- [ ] **Step 2: Full verification.**
  - **Backend** (from `backend/`): `"$UV" run ruff check .` and `"$UV" run manage.py test hub analytics`.
  - **Frontend:** `npm run lint`, `npm test`, `node scripts/check-locales.mjs` and the build.
  - Expected: all pass, and locales are unchanged.

- [ ] **Step 3: Commit and rollout note.** Commit `docs: rich-text formatting`. On the VM, `git pull` then `docker compose up -d --build frontend` (backend too for Task 5: `backend celery`). There are no migrations. Then check page 334 on the live site: the table fills the width.
