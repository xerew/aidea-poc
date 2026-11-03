# Rich-text formatting — Design

Date: 2026-11-03 · Status: builder-checked, awaiting product-owner review

## Intent

Partner feedback on the text-resource editor:
- **Missing tools:** authors miss the formatting every authoring tool or LMS has. They want text colour, alignment, spacing, table formatting, fonts and font sizes.
- **"Old style" font:** the paragraph font looks old-fashioned. The cause is a bug: the editor frame inherits the browser's default serif font, while learners see Lexend.
- **Cramped tables:** a table on a live page (course 29, page 334) looks cramped. The learner view renders tables with `display: block`, so they shrink to their content instead of filling the page.

**Goal:** authors can make pages look the way they intend, and learners see exactly that. Pages stay readable on phones, safe to display, and translatable into the 9 platform languages.

## Goals

1. **The editor shows what learners will see:** the same fonts, sizes, spacing and table look.
2. **Text:**
   - a font picker with a curated font list;
   - font sizes in named steps;
   - text colour from a fixed palette;
   - light highlight colours.
3. **Paragraphs:**
   - alignment: left, centre, right, justify;
   - line spacing: 1, 1.15, 1.5, 2;
   - space before/after: small, normal, large;
   - indent in and out.
4. **Tables:**
   - column widths;
   - cell padding and cell text alignment (horizontal and vertical);
   - borders on or off;
   - header row and/or header column;
   - cell background from the palette's light tints;
   - striped rows.
5. **Tables fill the page width for learners,** and wide tables scroll sideways on narrow screens.
6. **Pasting from Word or the web** keeps what the platform allows and removes the rest.
7. **All fonts are served from our own server,** including the platform's existing Lexend and Oswald. No page loads anything from Google Fonts.

## Non-goals

- Free colour picking (any colour), point sizes, or fonts outside the curated list.
- Changing existing course content. Old pages keep rendering as today, except that tables now fill the width (Goal 5).
- The "no review needed (reflection)" assignment setting. It gets its own spec.
- More block types (h1, h4, code blocks) or other editor plugins (embeds, emoji, etc.).

## Anti-goals (a failure even if it technically works)

- **Unreadable pages:** low-contrast text, tiny text on phones, or a table you can't read on a phone.
- **Unsafe styling reaching learners.** Any style beyond the exact allowed properties and values must never be displayed. For example:
  - `position: fixed` overlays;
  - `url(...)` backgrounds;
  - huge sizes;
  - hidden text;
  - anything that could cover the page or load something from outside.
- **Formatting that breaks translation.** A translated page must never lose its text or structure.
- **Learner data sent to a third party** (Google) just to show a font.

## Constraints and existing state

- **The single allow-list** is `frontend/src/lib/richText.js`:
  - `RICH_TEXT_VALID_ELEMENTS` for TinyMCE 8;
  - `SANITIZE_CONFIG` for DOMPurify;
  - the image-src hook.
  - It stays the one source for both the editor and the learner view.
- **Where content is cleaned:**
  - The backend does not sanitise rich text. Learners' HTML is cleaned when displayed (`components/lesson/HtmlContent.jsx`, DOMPurify).
  - The editor also restricts content (`components/lesson/RichTextEditor.jsx`).
  - This model stays: the display-time cleaning is the safety net.
- **Translation** (`backend/hub/html_translate.py`):
  - Translates rich text block by block (`p`, `h2`, `h3`, `li`, `td`, `th`, `caption`, `blockquote`).
  - It replaces only a block's inner content, so attributes on the block element itself (e.g. `style` on `p`/`td`) survive.
  - A structure check (`_signature`: tag counts, link hrefs, image placeholders) rejects a model answer whose tags differ. After two failed tries, the block falls back to its plain text.
  - So inline formatting (spans) inside a block can be lost in one language. **That is accepted (decision below).**
  - `span` is already in its rich-text tag list but not in the editor/DOMPurify allow-list. This change adds it.
- **Fonts today:** Lexend and Oswald load from `fonts.googleapis.com` (`frontend/index.html`).
  - `@fontsource-variable/geist` is already a dependency, so fontsource packages are the established way to self-host.
  - **Lexend has no Greek glyphs.** Greek text currently falls back to whatever the device has.
- **No dark mode.** Palette contrast is checked against white.
- **The 9 locales** (en, el, fr, es, it, fi, sv, no, de) must stay in sync for any new UI strings, such as palette colour names and step names if shown.

## Decisions (made by the product owner)

| Topic | Decision |
|---|---|
| Text colour | **Fixed palette** of about 8–10 colours that match the platform and pass contrast on white. No free picker. |
| Highlight | **Yes:** a few light background tints (yellow, green, blue, pink) for marking key terms. |
| Fonts | **Font picker with a curated set of about 8 fonts.** Lexend stays the default. |
| Font hosting | **Self-hosted, for all fonts,** including Lexend and Oswald. Remove the Google Fonts links. |
| Font sizes | **Named steps:** Small, Normal, Large, Extra large, Huge. Relative to the page, so they follow the learner's zoom. No point sizes. |
| Paragraph controls | Alignment, line spacing, space before/after, indent: all four. |
| Table controls | Column widths, cell padding and alignment, borders and header style (including cell background from the palette), striped rows: all four. |
| Pasting | **Keep what we allow.** Bold/italic/underline, lists, tables, alignment and spacing stay. Colours snap to the nearest palette colour. Everything else is dropped. |
| Translation trade-off | **Keep the text, drop that colour.** If inline formatting makes a block fail the structure check, the block is still translated and its inline formatting may be lost in that language only. Block-level formatting (alignment, spacing, cell styles) is always kept. |

## Decisions (designer's calls, open to correction)

- **Font list:** every font except Lexend must include Greek, so Greek courses look as designed. Proposed set (checked: these fontsource packages ship Greek files):
  - **Lexend** (default)
  - **Inter**
  - **Open Sans**
  - **Roboto**
  - **Noto Sans**
  - **Noto Serif** (serif)
  - **Literata** (serif, for reading)
  - **Fira Code** (monospace, for prompts and code)
  - Merriweather, Lora and Atkinson Hyperlegible were rejected: no Greek.
- **Greek fallback for the default font:** the default stack becomes Lexend → Noto Sans → system. Greek text then renders consistently in Noto Sans instead of a random device font. This also improves today's pages.
- **Size steps:** Small 0.875em, Normal 1em, Large 1.25em, Extra large 1.5em, Huge 2em.
- **Palette:**
  - **Text colours:** about 8–10, each with contrast ≥ 4.5:1 on white (WCAG AA for normal text), drawn from the platform's own colours plus common needs (dark red, dark green, dark blue, purple, orange-brown, grey). The builder picks exact hex values and verifies contrast.
  - **Highlight tints:** 4, light enough that black text on them keeps ≥ 4.5:1.
  - **Table cell backgrounds:** the same 4 tints plus a light grey.
- **Paste rules:**
  - Font families outside the list are dropped, so the text falls back to the default.
  - Font sizes not matching a step are dropped.
  - Colours snap to the nearest palette colour, by perceptual distance.
- **Only exact allowed values survive.** The allow-list names each allowed CSS property and its allowed values: palette colours, size steps, listed fonts, the fixed spacing steps, alignment keywords, bounded indent and column-width percentages. Any other declaration is removed in the editor and again at display.

## How it should behave

**Author (editor):**
- The toolbar gains:
  - a font family list;
  - a font size list (the 5 named steps);
  - text colour and highlight (palette only);
  - alignment;
  - line spacing;
  - space before/after;
  - indent in and out.
- The table toolbar and dialogs offer:
  - column width;
  - cell padding (e.g. compact, normal, roomy);
  - cell alignment;
  - borders on or off;
  - header row/column;
  - cell background (tints);
  - striped rows.
- The editor frame loads the same fonts and the same rich-text stylesheet as the learner view, so what the author sees is what learners see.
- Existing pages open and save unchanged unless edited.

**Learner (display):**
- Allowed formatting renders exactly as the author set it; anything else is removed silently.
- **Tables:**
  - They fill the content width.
  - Column widths are respected.
  - On narrow screens a wide table scrolls sideways inside its own area, and the page itself never scrolls sideways.
  - Striped rows and header styles render as set.

**Translation:**
- Block-level styles are kept automatically, because only the block's inner content is replaced.
- Inline spans (font, size, colour, highlight) go to the model as part of the block. If the answer keeps the same tags, the formatting survives. If not, the block falls back to plain translated text.
- No change to the status, flags or review behaviour.

## Testing expectations

- **Allow-list (frontend unit tests on the shared `richText.js` helpers):**
  - Each allowed property and value survives.
  - Disallowed ones are removed:
    - off-palette colours;
    - `position`, `url()` backgrounds;
    - `expression(...)`, `behavior`;
    - huge or negative sizes, `display: none`;
    - unknown fonts;
    - out-of-range indent and widths.
  - Paste rules: snapping to the nearest palette colour, dropping unknown fonts and sizes.
- **Translation (backend):**
  - `style` on `p`/`td`/`th` survives translation unchanged.
  - A block with a styled span keeps the span when the model preserves it.
  - It falls back to plain text when the model doesn't.
- **Learner view:**
  - A table with column widths fills the width.
  - Old content (no styles) renders as before.
- **No requests to Google Fonts:** `index.html` and the CSS reference only bundled fonts.
- **Locales:** parity check passes if new strings were added.

## Answers from the builder check (designer's calls)

- **Storage: inline `style` attributes.**
  - Why: TinyMCE's native buttons write them, and stored HTML stays portable to the xlsx course transfer.
  - **Who displays rich text:** only the browser (`HtmlContent`, `ResourceView`, `OriginalHint`). No emails, PDFs or other consumers.
  - **Filtering:**
    - DOMPurify allows the `style` attribute.
    - A shared declaration filter in `richText.js` runs as a DOMPurify hook. It parses each `style`, keeps only allowed property/value pairs, and drops the attribute when nothing is left.
    - The editor uses the same filter: on paste, and through TinyMCE's `valid_styles` plus a pre-save/content filter, so the editor can't keep what display would drop.
- **Translation fallback gets one intermediate step.**
  - When a block fails the structure check twice, retry once with styled `span`s unwrapped (their text kept, the span removed). Bold, italic, links and images stay, so the block keeps everything except the inline font, size, colour and highlight.
  - Only if that also fails, fall back to plain text as today.
  - This matches "keep the text, drop that colour" more closely than going straight to plain text.
  - The prompt already says "keep every HTML tag and attribute exactly", so it needs no change.
- **Table width and scrolling:**
  - Tables are `width: 100%` with column widths in percentages.
  - Each table gets a minimum readable width (cells don't shrink below roughly 6–8 characters). When a phone is narrower than that, the table scrolls sideways inside a wrapper.
  - The wrapper is added at display time: after sanitising, each `table` is wrapped in a scroll container. Stored HTML never contains the wrapper.
  - The old `display: block` rule is removed.
- **TinyMCE (GPL core only, no premium plugins):**
  - Font family, font size, colour, alignment, line height, indent, table, and the paste hooks (`paste_preprocess`/`paste_postprocess`) are core.
  - **Custom formats and toolbar buttons are expected** for space before/after, cell padding presets and striped rows. These are custom work, not missing features.
- **Colour snapping applies to paste only.** Existing content has no styles.
- **Fonts load on demand.**
  - Each font is declared with `@font-face` and `unicode-range` (as fontsource does), so a browser downloads a font file only when a page actually uses that font and those characters. Nothing extra loads up front.
  - Bundle regular, bold and italic for the picker fonts.
  - Lexend keeps its current weights.
  - Noto Sans sits in the default stack only as the Greek fallback.
- **No new locale strings for palette or step names.**
  - The TinyMCE interface is in English today (no `language` configured), so swatch tooltips and step names follow the editor's language.
  - Platform locales change only if a platform (non-TinyMCE) string is added.

## Left to the builder

- **Declaration filter implementation:** a small parser of `prop: value` pairs is enough; no CSS library is needed.
- **Exact values:** hex values, padding/spacing values, indent step size and maximum, column-width granularity.
- **Font weights and styles to bundle:** keep the download small, e.g. regular, bold and italic only for picker fonts.
- **TinyMCE configuration details:** plugins, menus, dialogs, `content_css`, paste pre-processing.
