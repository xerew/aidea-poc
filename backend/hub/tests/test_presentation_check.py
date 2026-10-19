import io
import zipfile

from django.test import SimpleTestCase

from hub import presentation
from hub.presentation import PPTX_MAIN_TYPE, PresentationError, check_pptx

MACRO_TYPE = 'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml'


def make_pptx(slides=3, title='AI risks', main_type=PPTX_MAIN_TYPE, extra=None, drop=(), presentation_xml=None):
    """A minimal .pptx: just the parts check_pptx reads."""
    ids = ''.join(f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(slides))
    parts = {
        '[Content_Types].xml': (
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            f'<Override PartName="/ppt/presentation.xml" ContentType="{main_type}"/></Types>'
        ),
        'ppt/presentation.xml': presentation_xml or (
            '<?xml version="1.0"?><p:presentation '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<p:sldIdLst>{ids}</p:sldIdLst></p:presentation>'
        ),
        'docProps/core.xml': (
            '<?xml version="1.0"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            f'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title></cp:coreProperties>'
        ),
    }
    parts.update(extra or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            if name not in drop:
                z.writestr(name, data)
    buffer.seek(0)
    return buffer


class CheckPptxTests(SimpleTestCase):
    def code(self, fileobj):
        with self.assertRaises(PresentationError) as ctx:
            check_pptx(fileobj)
        return ctx.exception.code

    def test_valid_deck(self):
        f = make_pptx(slides=3, title='AI risks')
        info = check_pptx(f)
        self.assertEqual((info.title, info.slide_count), ('AI risks', 3))
        self.assertEqual(f.tell(), 0)

    def test_missing_title_is_empty(self):
        self.assertEqual(check_pptx(make_pptx(drop=('docProps/core.xml',))).title, '')

    def test_old_ppt_asks_to_convert(self):
        self.assertEqual(self.code(io.BytesIO(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\0' * 100)), 'convert_to_pptx')

    def test_odp_asks_to_convert(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('mimetype', 'application/vnd.oasis.opendocument.presentation')
            z.writestr('content.xml', '<x/>')
        buffer.seek(0)
        self.assertEqual(self.code(buffer), 'convert_to_pptx')

    def test_renamed_text_file_is_not_pptx(self):
        self.assertEqual(self.code(io.BytesIO(b'just some notes')), 'not_pptx')

    def test_word_document_is_not_pptx(self):
        docx_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
        f = make_pptx(main_type=docx_type, drop=('ppt/presentation.xml',), extra={'word/document.xml': '<w/>'})
        self.assertEqual(self.code(f), 'not_pptx')

    def test_macros_are_refused(self):
        self.assertEqual(self.code(make_pptx(main_type=MACRO_TYPE)), 'macros')
        self.assertEqual(self.code(make_pptx(extra={'ppt/vbaProject.bin': b'\0'})), 'macros')

    def test_broken_zip_is_corrupt(self):
        self.assertEqual(self.code(io.BytesIO(b'PK\x03\x04' + b'garbage' * 20)), 'corrupt')

    def test_unreadable_xml_is_corrupt(self):
        self.assertEqual(self.code(make_pptx(presentation_xml='<p:presentation><unclosed>')), 'corrupt')

    def test_oversized_xml_part_is_corrupt(self):
        big = '<p:presentation xmlns:p="x">' + ' ' * (presentation.MAX_XML_BYTES + 1) + '</p:presentation>'
        self.assertEqual(self.code(make_pptx(presentation_xml=big)), 'corrupt')

    def test_no_slides(self):
        self.assertEqual(self.code(make_pptx(slides=0)), 'no_slides')

    def test_position_reset_after_error(self):
        f = io.BytesIO(b'just some notes')
        self.code(f)
        self.assertEqual(f.tell(), 0)


def _patch_central(buffer, name, offset, value):
    """Overwrite one little-endian 2-byte field of `name`'s central-directory entry."""
    data = bytearray(buffer.getvalue())
    marker = b'PK\x01\x02'
    pos = data.find(marker)
    while pos != -1:
        name_len = int.from_bytes(data[pos + 28:pos + 30], 'little')
        if data[pos + 46:pos + 46 + name_len].decode() == name:
            data[pos + offset:pos + offset + 2] = value.to_bytes(2, 'little')
            return io.BytesIO(bytes(data))
        pos = data.find(marker, pos + 4)
    raise AssertionError(f'{name} not found')


class DamagedZipTests(SimpleTestCase):
    def code(self, fileobj):
        with self.assertRaises(PresentationError) as ctx:
            check_pptx(fileobj)
        return ctx.exception.code

    def test_corrupted_deflate_data_is_corrupt(self):
        buffer = make_pptx(slides=40)
        with zipfile.ZipFile(buffer) as z:
            info = z.getinfo('ppt/presentation.xml')
        data = bytearray(buffer.getvalue())
        start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        for i in range(start + 2, start + min(info.compress_size, 40)):
            data[i] ^= 0xFF
        self.assertEqual(self.code(io.BytesIO(bytes(data))), 'corrupt')

    def test_unsupported_compression_is_corrupt(self):
        self.assertEqual(self.code(_patch_central(make_pptx(), 'ppt/presentation.xml', 10, 9)), 'corrupt')

    def test_encrypted_entry_is_corrupt(self):
        self.assertEqual(self.code(_patch_central(make_pptx(), 'ppt/presentation.xml', 8, 1)), 'corrupt')
