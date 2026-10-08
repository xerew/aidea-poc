import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    Course,
    H5PPackage,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    UserProfile,
)


def make_course(title='H5P course', creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-h5p', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(
        title=title, pillar=pillar, level='beginner', duration_hours=1, is_published=True,
        created_by=creator,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='A', order=1)
    resource = Resource.objects.create(activity=activity, type='h5p', order=1)
    return course, module, activity, resource


def make_h5p(main='H5P.MultiChoice', title='Quiz one', drop=(), extra=None, meta=None):
    """An in-memory .h5p archive: h5p.json, content.json and the library folders."""
    deps = [
        {'machineName': main, 'majorVersion': 1, 'minorVersion': 16},
        {'machineName': 'H5P.Question', 'majorVersion': 1, 'minorVersion': 5},
    ]
    files = {
        'h5p.json': json.dumps(meta if meta is not None else {
            'title': title, 'mainLibrary': main, 'language': 'en',
            'embedTypes': ['iframe'], 'preloadedDependencies': deps,
        }),
        'content/content.json': '{}',
        f'{main}-1.16/library.json': '{}',
        f'{main}-1.16/js/main.js': '',
        'H5P.Question-1.5/library.json': '{}',
    }
    files.update(extra or {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, data in files.items():
            if not any(name.startswith(d) for d in drop):
                zf.writestr(name, data)
    buf.seek(0)
    return buf


class H5PModelTests(TestCase):
    def setUp(self):
        self.course, self.module, self.activity, self.resource = make_course()

    def _package(self, language=''):
        return H5PPackage.objects.create(
            resource=self.resource, language=language, file='h5p_uploads/x.h5p',
            folder='h5p/abc', main_library='H5P.MultiChoice',
        )

    def test_one_package_per_language(self):
        self._package('')
        self._package('el')
        with self.assertRaises(IntegrityError):
            self._package('el')

    def test_media_path(self):
        self.assertEqual(self._package().media_path, '/media/h5p/abc')

    def test_resource_defaults(self):
        self.assertEqual(Resource.Type.H5P, 'h5p')
        self.assertFalse(self.resource.h5p_self_complete)

    def test_event_types(self):
        self.assertEqual(
            (LearningEvent.Type.H5P_ANSWER, LearningEvent.Type.H5P_ATTEMPT, LearningEvent.Type.H5P_ERROR),
            ('h5p_answer', 'h5p_attempt', 'h5p_error'),
        )


TMP_MEDIA = tempfile.mkdtemp(prefix='aidea-h5p-test-')

from hub import h5p  # noqa: E402  (module under test)


class ExtractPackageTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='aidea-h5p-x-'))
        self.dest = self.root / 'pkg'

    def assertCode(self, code, archive):
        with self.assertRaises(h5p.H5PError) as ctx:
            h5p.extract_package(archive, self.dest)
        self.assertEqual(ctx.exception.code, code)
        self.assertFalse(self.dest.exists(), 'nothing may be left behind')

    def test_valid_package_is_unpacked(self):
        info = h5p.extract_package(make_h5p(), self.dest)
        self.assertEqual((info.title, info.main_library), ('Quiz one', 'H5P.MultiChoice'))
        self.assertTrue((self.dest / 'h5p.json').is_file())
        self.assertTrue((self.dest / 'H5P.MultiChoice-1.16' / 'js' / 'main.js').is_file())
        self.assertGreater(info.unpacked_bytes, 0)

    def test_mac_metadata_and_dotfiles_are_ignored(self):
        h5p.extract_package(make_h5p(extra={'__MACOSX/._h5p.json': 'x', 'content/.DS_Store': 'x'}), self.dest)
        self.assertFalse((self.dest / '__MACOSX').exists())
        self.assertFalse((self.dest / 'content' / '.DS_Store').exists())

    def test_not_a_zip(self):
        self.assertCode('not_zip', io.BytesIO(b'definitely not a zip'))

    def test_missing_h5p_json(self):
        self.assertCode('no_h5p_json', make_h5p(drop=('h5p.json',)))

    def test_unreadable_h5p_json(self):
        self.assertCode('no_h5p_json', make_h5p(meta='not json'.split()))

    def test_missing_content(self):
        self.assertCode('no_content', make_h5p(drop=('content/',)))

    def test_disallowed_extension(self):
        self.assertCode('bad_extension', make_h5p(extra={'content/page.html': '<script></script>'}))

    def test_path_traversal_is_rejected(self):
        self.assertCode('unsafe_path', make_h5p(extra={'../evil.js': 'x'}))
        self.assertFalse((self.root / 'evil.js').exists())

    def test_missing_libraries(self):
        self.assertCode('missing_libraries', make_h5p(drop=('H5P.Question-1.5/',)))
        self.assertCode('missing_libraries', make_h5p(drop=('H5P.MultiChoice-1.16/',)))

    def test_unpacked_size_limit(self):
        with mock.patch.object(h5p, 'MAX_UNPACKED_BYTES', 10):
            self.assertCode('too_large_unpacked', make_h5p())

    def test_entry_count_limit(self):
        with mock.patch.object(h5p, 'MAX_ENTRIES', 2):
            self.assertCode('too_many_files', make_h5p())

    def test_default_self_complete(self):
        self.assertTrue(h5p.default_self_complete('H5P.Accordion'))
        self.assertFalse(h5p.default_self_complete('H5P.QuestionSet'))
        self.assertFalse(h5p.default_self_complete('H5P.InteractiveVideo'))


def upload_file(archive, name='activity.h5p'):
    return SimpleUploadedFile(name, archive.getvalue(), content_type='application/zip')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class AuthoringH5PTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.creator = User.objects.create_user('h5p_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.course, self.module, self.activity, self.resource = make_course(creator=self.creator)
        self.url = reverse('authoring-resource-h5p', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id,
            'lesson_pk': self.activity.id, 'resource_pk': self.resource.id,
        })
        self.client.force_authenticate(self.creator)

    def post(self, archive, language=''):
        return self.client.post(self.url, {'file': upload_file(archive), 'language': language}, format='multipart')

    def test_upload_main_file(self):
        res = self.post(make_h5p())
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        pkg = H5PPackage.objects.get(resource=self.resource)
        self.assertEqual((pkg.language, pkg.main_library, pkg.version), ('', 'H5P.MultiChoice', 1))
        self.assertTrue((Path(TMP_MEDIA) / pkg.folder / 'h5p.json').is_file())
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'Quiz one')       # taken from h5p.json
        self.assertFalse(self.resource.h5p_self_complete)
        self.assertEqual(res.data['h5p_packages'][0]['path'], f'/media/{pkg.folder}')

    def test_no_question_type_defaults_to_self_complete(self):
        self.post(make_h5p(main='H5P.Accordion'))
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.h5p_self_complete)

    def test_language_versions(self):
        self.post(make_h5p())
        self.assertEqual(self.post(make_h5p(title='Κουίζ'), language='el').status_code, 201)
        self.assertEqual(sorted(p.language for p in self.resource.h5p_packages.all()), ['', 'el'])
        self.assertEqual(self.post(make_h5p(), language='xx').status_code, 400)

    def test_replace_keeps_old_folder(self):
        self.post(make_h5p())
        old = H5PPackage.objects.get(resource=self.resource)
        self.post(make_h5p(title='Quiz two'))
        new = H5PPackage.objects.get(resource=self.resource)
        self.assertEqual(new.version, 2)
        self.assertNotEqual(new.folder, old.folder)
        self.assertTrue((Path(TMP_MEDIA) / old.folder / 'h5p.json').is_file())

    def test_bad_package_reports_code(self):
        res = self.post(make_h5p(extra={'content/page.html': 'x'}))
        self.assertEqual((res.status_code, res.data['code']), (400, 'bad_extension'))
        self.assertFalse(H5PPackage.objects.exists())

    def test_too_large(self):
        with mock.patch.object(h5p, 'MAX_FILE_BYTES', 10):
            res = self.post(make_h5p())
        self.assertEqual((res.status_code, res.data['code']), (400, 'too_large'))

    def test_only_h5p_resources(self):
        self.resource.type = 'text'
        self.resource.save()
        self.assertEqual(self.post(make_h5p()).status_code, 400)

    def test_permissions(self):
        other = User.objects.create_user('h5p_other', password='pass12345')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(other)
        self.assertEqual(self.post(make_h5p()).status_code, 403)
        teacher = User.objects.create_user('h5p_t', password='pass12345')
        UserProfile.objects.create(user=teacher, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(teacher)
        self.assertEqual(self.post(make_h5p()).status_code, 403)

    def test_delete_language_version(self):
        self.post(make_h5p())
        self.post(make_h5p(), language='el')
        res = self.client.delete(f'{self.url}?language=el')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([p.language for p in self.resource.h5p_packages.all()], [''])
        self.assertEqual(self.client.delete(f'{self.url}?language=fr').status_code, 404)

    def test_self_complete_is_editable(self):
        detail = reverse('authoring-resource-detail', kwargs={
            'pk': self.course.id, 'module_pk': self.module.id,
            'lesson_pk': self.activity.id, 'resource_pk': self.resource.id,
        })
        self.client.patch(detail, {'h5p_self_complete': True}, format='json')
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.h5p_self_complete)

    def test_copy_module_copies_packages(self):
        from hub.views.authoring_module_library import copy_module
        self.post(make_h5p())
        self.post(make_h5p(), language='el')
        target, *_ = make_course(title='Target', creator=self.creator)
        new_module = copy_module(self.module, target, order=2)
        copied = Resource.objects.get(activity__module=new_module)
        self.assertEqual(sorted(p.language for p in copied.h5p_packages.all()), ['', 'el'])
        self.assertEqual(
            {p.folder for p in copied.h5p_packages.all()},
            {p.folder for p in self.resource.h5p_packages.all()},
        )
