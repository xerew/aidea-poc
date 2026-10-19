import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import CourseEditHistory, PresentationFile, UserProfile
from hub.views.authoring_module_library import copy_module

from .test_presentation_check import make_pptx
from .test_presentation_models import make_presentation_resource

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-api-')


def deck(name='deck.pptx', **kw):
    return SimpleUploadedFile(name, make_pptx(**kw).read(),
                              content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')


@override_settings(MEDIA_ROOT=MEDIA)
class PresentationAPITests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user('pres_cc', password='x')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_presentation_resource(creator=self.creator)
        self.url = reverse('authoring-resource-presentation', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id,
            'resource_pk': self.resource.id})
        self.client.force_authenticate(self.creator)

    def upload(self, language='', **kw):
        return self.client.post(self.url, {'file': deck(**kw), 'language': language}, format='multipart')

    def test_upload_main_deck(self):
        res = self.upload(slides=4, title='AI risks')
        self.assertEqual(res.status_code, 201, res.data)
        [info] = res.data['presentation_files']
        self.assertEqual((info['language'], info['slide_count'], info['title'], info['version'],
                          info['over_viewer_limit']), ('', 4, 'AI risks', 1, False))
        self.assertTrue(info['path'].startswith('/media/presentations/'))
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'AI risks')            # first main deck names an untitled resource
        self.assertTrue(CourseEditHistory.objects.filter(course=self.course).exists())

    def test_title_falls_back_to_file_name(self):
        res = self.client.post(self.url, {'file': deck('Week 1 slides.pptx', title=''), 'language': ''}, format='multipart')
        self.assertEqual(res.data['presentation_files'][0]['title'], 'Week 1 slides')

    def test_errors_have_codes(self):
        bad = SimpleUploadedFile('notes.pptx', b'plain text')
        self.assertEqual(self.client.post(self.url, {'file': bad}, format='multipart').data['code'], 'not_pptx')
        self.assertEqual(self.client.post(self.url, {}, format='multipart').data['code'], 'no_file')
        self.assertEqual(self.upload(language='xx').data['code'], 'bad_language')
        with override_settings(PRESENTATION_MAX_MB=0):
            self.assertEqual(self.upload().data['code'], 'too_large')

    def test_replace_deletes_old_file_and_bumps_version(self):
        self.upload()
        self.upload(language='el')
        old = PresentationFile.objects.get(resource=self.resource, language='')
        old_path = Path(MEDIA) / old.file.name
        res = self.upload(slides=7)
        main = next(p for p in res.data['presentation_files'] if p['language'] == '')
        self.assertEqual((main['version'], main['slide_count']), (2, 7))
        self.assertFalse(old_path.exists())
        self.assertTrue(PresentationFile.objects.filter(resource=self.resource, language='el', version=1).exists())

    def test_delete_language_version(self):
        self.upload()
        self.upload(language='el')
        el = PresentationFile.objects.get(resource=self.resource, language='el')
        path = Path(MEDIA) / el.file.name
        res = self.client.delete(f'{self.url}?language=el')
        self.assertEqual([p['language'] for p in res.data['presentation_files']], [''])
        self.assertFalse(path.exists())
        self.assertEqual(self.client.delete(f'{self.url}?language=el').status_code, 404)

    def test_permissions_and_type(self):
        other = User.objects.create_user('pres_other', password='x')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.upload().status_code, 403)
        learner = User.objects.create_user('pres_l', password='x')
        UserProfile.objects.create(user=learner)
        self.client.force_authenticate(learner)
        self.assertEqual(self.upload().status_code, 403)
        self.client.force_authenticate(self.creator)
        self.resource.type = 'pdf'
        self.resource.save()
        self.assertEqual(self.upload().data['code'], 'not_presentation')

    def test_download_flag_saved_through_resource_patch(self):
        url = reverse('authoring-resource-detail', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id, 'lesson_pk': self.activity.id,
            'resource_pk': self.resource.id})
        res = self.client.patch(url, {'presentation_downloadable': True}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['presentation_downloadable'])

    def test_copied_module_gets_its_own_deck_file(self):
        self.upload()
        new_module = copy_module(self.module, self.course, order=2)
        copy = PresentationFile.objects.get(resource__activity__module=new_module)
        original = PresentationFile.objects.get(resource=self.resource)
        self.assertNotEqual(copy.file.name, original.file.name)
        self.upload(slides=9)                                        # replace in the original
        self.assertTrue((Path(MEDIA) / copy.file.name).exists())
        self.assertEqual((copy.slide_count, copy.title, copy.version), (original.slide_count, original.title, 1))


class CaddyConfigTests(APITestCase):
    def test_caddy_caps_presentation_uploads_and_sets_file_headers(self):
        from django.conf import settings
        text = (Path(settings.BASE_DIR).parent / 'Caddyfile').read_text(encoding='utf-8')
        self.assertIn('path_regexp ^/api/authoring/.*/presentation/$', text)
        self.assertIn('header /media/presentations/*', text)
        self.assertIn('application/vnd.openxmlformats-officedocument.presentationml.presentation', text)
