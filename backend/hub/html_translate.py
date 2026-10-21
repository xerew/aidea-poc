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
_HTML = re.compile(r'</?[a-z][^>]*>', re.I)


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


def _translate_block(el, translate_fragment, translate_plain):
    if not el.text_content().strip():
        return
    originals = _swap_images(el)
    fragment = _inner(el)
    expected = _signature(_parse(fragment))
    for _ in range(2):
        answer = translate_fragment(fragment)
        try:
            candidate = _parse(answer)
        except (etree.ParserError, ValueError):
            continue
        if _signature(candidate) == expected:
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


def translate_html(html, translate_fragment, translate_plain):
    root = _parse(html)
    for img in root.iter('img'):
        if (img.get('alt') or '').strip():
            img.set('alt', translate_plain(img.get('alt')))
    blocks = [e for e in _elements(root) if _is_leaf_block(e)]
    if not blocks:                  # inline-only content, e.g. 'Hello <b>world</b>'
        blocks = [root]
    for el in blocks:
        _translate_block(el, translate_fragment, translate_plain)
    if blocks != [root]:            # stray text between top-level blocks
        if (root.text or '').strip():
            root.text = translate_plain(root.text)
        for child in root:
            if (child.tail or '').strip():
                child.tail = translate_plain(child.tail)
    return _inner(root)
