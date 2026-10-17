import tempfile
from pathlib import Path

import docx
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw

from hub.ai_review import evidence
from hub.models import AIReview, AssignmentSubmission, UserProfile

from .test_ai_review_models import make_assignment

MEDIA = tempfile.mkdtemp(prefix='aidea-air-media-')

def make_pdf(text):
    """Smallest valid one-page PDF showing `text` (with a correct xref table)."""
    stream = f'BT /F1 18 Tf 20 60 Td ({text}) Tj ET'.encode()
    objects = [
        b'<</Type/Catalog/Pages 2 0 R>>',
        b'<</Type/Pages/Kids[3 0 R]/Count 1>>',
        b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>',
        b'<</Length %d>>stream\n' % len(stream) + stream + b'\nendstream',
        b'<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>',
    ]
    out, offsets = bytearray(b'%PDF-1.4\n'), []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj' % n + body + b'endobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)
    out += b''.join(b'%010d 00000 n \n' % o for o in offsets)
    out += b'trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF' % (len(objects) + 1, xref)
    return bytes(out)


PDF = make_pdf('Risk register')


def write(name, data):
    path = Path(MEDIA) / 'submission_uploads' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data)
    return path


def picture(name, shift=0, size=(400, 300)):
    img = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50 + shift, 50, 250 + shift, 200], fill='navy')
    draw.ellipse([260, 60, 380, 180], fill='orange')
    path = Path(MEDIA) / 'submission_uploads' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def url(path):
    return f'http://testserver/media/{path.relative_to(MEDIA).as_posix()}'


@override_settings(MEDIA_ROOT=MEDIA, MEDIA_URL='/media/')
class EvidenceTests(TestCase):
    def setUp(self):
        *_, self.activity, self.resource = make_assignment()

    def submission(self, username, attachments, text=''):
        user = User.objects.create_user(username, password='x', first_name=username.title())
        UserProfile.objects.create(user=user)
        return AssignmentSubmission.objects.create(
            user=user, lesson=self.activity, resource=self.resource, text=text, attachments=attachments,
        )

    def test_media_path_inside_media_root_only(self):
        good = write('a.txt', 'hello')
        self.assertEqual(evidence.media_path(url(good)), good.resolve())
        self.assertIsNone(evidence.media_path('http://testserver/media/../../etc/passwd'))
        self.assertIsNone(evidence.media_path('https://youtube.com/watch?v=x'))
        self.assertIsNone(evidence.media_path('http://testserver/media/submission_uploads/missing.png'))

    def test_extract_text_from_pdf_docx_txt(self):
        doc = docx.Document()
        doc.add_paragraph('Mitigation plan')
        docx_path = Path(MEDIA) / 'submission_uploads' / 'plan.docx'
        doc.save(docx_path)
        self.assertIn('Risk register', evidence.extract_text(write('r.pdf', PDF)))
        self.assertIn('Mitigation plan', evidence.extract_text(docx_path))
        self.assertEqual(evidence.extract_text(write('n.txt', 'notes')), 'notes')

    def test_corrupt_files_are_skipped(self):
        self.assertEqual(evidence.extract_text(write('bad.pdf', b'not a pdf')), '')
        self.assertIsNone(evidence.image_b64(write('fake.png', b'not an image')))
        self.assertEqual(evidence.fingerprint(write('fake2.png', b'xx'))['dhash'], '')

    def test_images_are_resized_and_encoded(self):
        big = picture('big.png', size=(3000, 2000))
        encoded = evidence.image_b64(big)
        import base64
        import io
        with Image.open(io.BytesIO(base64.b64decode(encoded))) as img:
            self.assertLessEqual(max(img.size), evidence.MAX_IMAGE_SIDE)

    def test_gather_collects_everything(self):
        shot = picture('shot.png')
        pdf = write('report.pdf', PDF)
        sub = self.submission('ann', [
            {'type': 'image', 'url': url(shot), 'name': 'shot.png'},
            {'type': 'file', 'url': url(pdf), 'name': 'report.pdf'},
            {'type': 'video', 'url': 'https://youtu.be/x', 'name': 'demo'},
        ], text='My answer')
        ev = evidence.gather(sub)
        self.assertEqual(ev.text, 'My answer')
        self.assertEqual([i['name'] for i in ev.images], ['shot.png'])
        self.assertEqual([d['name'] for d in ev.documents], ['report.pdf'])
        self.assertEqual(ev.links, ['demo (https://youtu.be/x)'])
        self.assertEqual(len(ev.fingerprints), 2)

    def test_duplicates_identical_and_similar(self):
        original = picture('orig.png')
        same = write('copy.png', original.read_bytes())
        resized = picture('resized.png', shift=2)      # nearly the same picture
        other = self.submission('bob', [{'type': 'image', 'url': url(original), 'name': 'orig.png'}])
        AIReview.objects.create(submission=other, rubric=[], status='done',
                                checks={'fingerprints': [evidence.fingerprint(original) | {'name': 'orig.png'}]})
        mine = self.submission('cat', [])
        prints = [evidence.fingerprint(same) | {'name': 'copy.png'}, evidence.fingerprint(resized) | {'name': 'resized.png'}]
        dupes = evidence.find_duplicates(mine, prints)
        self.assertEqual({(d['file'], d['match']) for d in dupes}, {('copy.png', 'identical'), ('resized.png', 'similar')})
        self.assertEqual(dupes[0]['learner'], 'Bob')
        self.assertEqual(evidence.find_duplicates(other, prints), [])   # never against your own work
