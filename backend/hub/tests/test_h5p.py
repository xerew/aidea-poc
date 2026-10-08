import io
import json
import tempfile
import zipfile

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from hub.models import (
    Activity,
    Course,
    H5PPackage,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
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
User  # re-exported for later test classes in this module
