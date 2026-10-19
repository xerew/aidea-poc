"""Checking uploaded PowerPoint decks (.pptx) for presentation resources.

Only what the slideshow needs is read: the content types (is it a real,
macro-free presentation?), the slide list and the title. Parts are size-capped
before parsing so a crafted file cannot exhaust memory."""
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

PPTX_MAIN_TYPE = 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
MACRO_MAIN_TYPE = 'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml'
OLE_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'      # .ppt and other pre-2007 Office files
ODF_PREFIX = b'application/vnd.oasis.opendocument'
NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
NS_DC = 'http://purl.org/dc/elements/1.1/'
MAX_XML_BYTES = 5 * 1024 * 1024

MESSAGES = {
    'not_pptx': 'This is not a PowerPoint (.pptx) file.',
    'convert_to_pptx': 'Save it as .pptx (in Impress: File → Save As → PowerPoint), then upload again.',
    'macros': 'Presentations with macros cannot be used. Save it as a normal .pptx.',
    'corrupt': 'The file is damaged or could not be read.',
    'no_slides': 'This presentation has no slides.',
}


class PresentationError(Exception):
    def __init__(self, code):
        super().__init__(MESSAGES[code])
        self.code = code
        self.detail = MESSAGES[code]


@dataclass
class DeckInfo:
    title: str
    slide_count: int


def _read(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_XML_BYTES:
        raise PresentationError('corrupt')
    return archive.read(name)


def _title(archive, names):
    if 'docProps/core.xml' not in names:
        return ''
    try:
        root = ElementTree.fromstring(_read(archive, 'docProps/core.xml'))
    except (ElementTree.ParseError, PresentationError):
        return ''
    node = root.find(f'{{{NS_DC}}}title')
    return (node.text or '').strip()[:255] if node is not None else ''


def _inspect(fileobj):
    head = fileobj.read(8)
    fileobj.seek(0)
    if head == OLE_MAGIC:
        raise PresentationError('convert_to_pptx')
    if not head.startswith(b'PK'):
        raise PresentationError('not_pptx')
    try:
        with zipfile.ZipFile(fileobj) as archive:
            names = set(archive.namelist())
            if 'mimetype' in names and _read(archive, 'mimetype').strip().startswith(ODF_PREFIX):
                raise PresentationError('convert_to_pptx')
            if '[Content_Types].xml' not in names:
                raise PresentationError('not_pptx')
            types = _read(archive, '[Content_Types].xml').decode('utf-8', 'replace')
            if MACRO_MAIN_TYPE in types or 'ppt/vbaProject.bin' in names:
                raise PresentationError('macros')
            if PPTX_MAIN_TYPE not in types or 'ppt/presentation.xml' not in names:
                raise PresentationError('not_pptx')
            root = ElementTree.fromstring(_read(archive, 'ppt/presentation.xml'))
            slides = root.find(f'{{{NS_P}}}sldIdLst')
            count = len(slides) if slides is not None else 0
            if count == 0:
                raise PresentationError('no_slides')
            return DeckInfo(title=_title(archive, names), slide_count=count)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ElementTree.ParseError, KeyError, OSError, EOFError):
        raise PresentationError('corrupt') from None


def check_pptx(fileobj):
    try:
        return _inspect(fileobj)
    finally:
        fileobj.seek(0)
