import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from hub.models import UserProfile

MEDIA_ROOT = tempfile.mkdtemp(prefix='aidea-test-media-')


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class AuthoringUploadTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.creator = User.objects.create_user(username='uploader', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type='content_creator')
        self.teacher = User.objects.create_user(username='not_creator', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type='teacher')
        self.url = '/api/authoring/upload/'

    def _pdf(self, name='doc.pdf', size=100):
        return SimpleUploadedFile(name, b'%PDF-1.4 ' + b'0' * size, content_type='application/pdf')

    def test_creator_can_upload_pdf(self):
        self.client.force_authenticate(self.creator)
        res = self.client.post(self.url, {'file': self._pdf()}, format='multipart')
        self.assertEqual(res.status_code, 201)
        self.assertIn('/media/lesson_uploads/', res.data['url'])
        self.assertTrue(res.data['url'].startswith('http'))

    def test_teacher_rejected(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.post(self.url, {'file': self._pdf()}, format='multipart')
        self.assertEqual(res.status_code, 403)

    def test_bad_extension_rejected(self):
        self.client.force_authenticate(self.creator)
        bad = SimpleUploadedFile('run.exe', b'MZ', content_type='application/octet-stream')
        res = self.client.post(self.url, {'file': bad}, format='multipart')
        self.assertEqual(res.status_code, 400)

    def test_oversize_rejected(self):
        self.client.force_authenticate(self.creator)
        big = SimpleUploadedFile('big.pdf', b'0' * (21 * 1024 * 1024), content_type='application/pdf')
        res = self.client.post(self.url, {'file': big}, format='multipart')
        self.assertEqual(res.status_code, 400)
