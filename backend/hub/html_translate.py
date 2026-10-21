"""Translate rich-text HTML block by block, keeping its structure — spec
docs/superpowers/specs/2026-10-21-rich-text-and-activity-completion-design.md §2.

Only the text inside paragraphs, headings, list items, table cells, captions
and quotes goes to the model; tables, lists, images and order stay as they
are. Images are swapped for bare placeholders, so the model never sees their
addresses. Every answer is checked (same tags, same link targets, same
placeholders); a bad answer is retried once, then that block is translated as
plain text (inline formatting dropped, images kept)."""
import re
from collections import Counter

from lxml import etree
from lxml import html as lhtml

BLOCK_TAGS = frozenset({'p', 'h2', 'h3', 'li', 'td', 'th', 'caption', 'blockquote'})
CONTAINER_TAGS = frozenset({'ul', 'ol', 'table', 'thead', 'tbody', 'tfoot', 'tr'})
# Only tags rich text actually uses count as HTML: "<role>" in a prompt is plain text.
_HTML = re.compile(
    r'</?(p|br|strong|b|em|i|u|h[1-6]|ul|ol|li|a|blockquote|table|thead|tbody|tfoot|tr|th|td|caption|img|span|div)'
    r'(\s[^>]*)?/?>', re.I)
_FENCE = re.compile(r'^\s*```[a-zA-Z]*[ \t]*\n?(.*?)\n?\s*```\s*$', re.S)
# Characters lxml refuses in text (a model may emit them); dropping them never loses meaning.
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
MAX_GROWTH = 3      # a translation more than 3x (+20 chars) the source text is chatter, not a translation


def _clean(text):
    return _CONTROL.sub('', text or '')


def looks_like_html(text):
    return bool(text) and bool(_HTML.search(text))


def _parse(fragment):
    return lhtml.fragment_fromstring(fragment, create_parent='div')


def _inner(el):
    return (el.text or '') + ''.join(etree.tostring(c, encoding='unicode', method='html') for c in el)


def _elements(root):
    return [e for e in root.iter() if isinstance(e.tag, str) and e is not root]


def _signature(root):
    elements = _elements(root)
    return (
        Counter(e.tag for e in elements),
        [e.get('href') for e in elements if e.tag == 'a'],
        sorted(e.get('data-k') or '' for e in elements if e.tag == 'img'),
    )


def _is_leaf_block(el):
    return el.tag in BLOCK_TAGS and not any(
        isinstance(d.tag, str) and d.tag in BLOCK_TAGS for d in el.iterdescendants())


def _swap_images(el):
    """Replace each <img> in `el` with <img data-k="i">; return the originals."""
    originals = []
    for i, img in enumerate(list(el.iter('img'))):
        placeholder = etree.Element('img', {'data-k': str(i)})
        placeholder.tail, img.tail = img.tail, None
        img.getparent().replace(img, placeholder)
        originals.append(img)
    return originals


def _restore_images(el, originals):
    for placeholder in [e for e in el.iter('img') if e.get('data-k') is not None]:
        original = originals[int(placeholder.get('data-k'))]
        original.tail = placeholder.tail
        placeholder.getparent().replace(placeholder, original)


def _set_inner(el, source):
    for child in list(el):
        el.remove(child)
    el.text = source.text
    for child in list(source):
        el.append(child)


def _acceptable(answer, fragment, expected, source_len):
    """The model's answer as a parsed fragment, or None when it isn't a
    faithful translation (different tags or links, chatter around it)."""
    fence = _FENCE.match(answer)
    if fence:
        answer = fence.group(1)
    if '\n' in answer.strip() and '\n' not in fragment:     # e.g. "Here is the translation:\n…"
        return None
    try:
        candidate = _parse(answer)
    except (etree.ParserError, ValueError):
        return None
    if _signature(candidate) != expected:
        return None
    if len(candidate.text_content().strip()) > MAX_GROWTH * source_len + 20:
        return None
    return candidate


def _translate_block(el, translate_fragment, translate_plain):
    if not el.text_content().strip():
        return
    originals = _swap_images(el)
    fragment = _inner(el)
    source = _parse(fragment)
    expected, source_len = _signature(source), len(source.text_content().strip())
    for _ in range(2):
        candidate = _acceptable(_clean(translate_fragment(fragment)), fragment, expected, source_len)
        if candidate is not None:
            _set_inner(el, candidate)
            _restore_images(el, originals)
            return
    # Plain-text fallback: the block keeps its place and its images.
    text = translate_plain(el.text_content())
    for child in list(el):
        el.remove(child)
    el.text = text
    for img in originals:
        el.append(img)


def _is_structural(node):
    return isinstance(node.tag, str) and (
        node.tag in BLOCK_TAGS or node.tag in CONTAINER_TAGS
        or any(isinstance(d.tag, str) and d.tag in BLOCK_TAGS for d in node.iterdescendants()))


def _translate_direct_text(el, translate_fragment, translate_plain):
    """The inline text of a block that also holds blocks — e.g. a list item
    with a sub-list ("Parent <b>text</b><ul>…</ul>"), translated like a block."""
    children = list(el)
    first = next((i for i, c in enumerate(children) if _is_structural(c)), len(children))
    leading = children[:first]
    if (el.text or '').strip() or any(c.text_content().strip() or (c.tail or '').strip() for c in leading):
        run = lhtml.Element('span')
        run.text, el.text = el.text, None
        for child in leading:
            el.remove(child)
            run.append(child)
        _translate_block(run, translate_fragment, translate_plain)
        el.text = run.text
        for index, child in enumerate(list(run)):
            el.insert(index, child)
    for child in children[first:]:
        if _is_structural(child) and (child.tail or '').strip():
            child.tail = translate_plain(child.tail)


def translate_html(html, translate_fragment, translate_plain):
    plain = translate_plain
    translate_plain = lambda text: _clean(plain(text))  # noqa: E731 — every model answer is cleaned
    root = _parse(html)
    for img in root.iter('img'):
        if (img.get('alt') or '').strip():
            img.set('alt', translate_plain(img.get('alt')))
    blocks = [e for e in _elements(root) if _is_leaf_block(e)]
    parents = [e for e in _elements(root) if e.tag in BLOCK_TAGS and not _is_leaf_block(e)]
    if not blocks:                  # inline-only content, e.g. 'Hello <b>world</b>'
        blocks = [root]
    for el in blocks:
        _translate_block(el, translate_fragment, translate_plain)
    for el in parents:
        _translate_direct_text(el, translate_fragment, translate_plain)
    if blocks != [root]:            # stray text between top-level blocks
        if (root.text or '').strip():
            root.text = translate_plain(root.text)
        for child in root:
            if (child.tail or '').strip():
                child.tail = translate_plain(child.tail)
    return _inner(root)
