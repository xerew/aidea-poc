import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from hub.models import (
    Activity,
    Course,
    LearningEvent,
    LearningPillar,
    Module,
    PresentationFile,
    Resource,
)

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-media-')


def make_presentation_resource(title='Deck course', creator=None):
    pillar = LearningPillar.objects.get_or_create(slug='p-pres', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=title, pillar=pillar, level='beginner', duration_hours=1,
                                   is_published=True, created_by=creator)
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='A', order=1, lesson_type='presentation')
    resource = Resource.objects.create(activity=activity, type='presentation', order=1)
    return course, module, activity, resource


@override_settings(MEDIA_ROOT=MEDIA)
class PresentationModelTests(TestCase):
    def test_types_and_defaults(self):
        *_, resource = make_presentation_resource()
        self.assertEqual(resource.get_type_display(), 'Presentation')
        self.assertFalse(resource.presentation_downloadable)
        self.assertIn('presentation_download', LearningEvent.Type.values)
        event_type = LearningEvent._meta.get_field('event_type')
        self.assertGreaterEqual(event_type.max_length, len('presentation_download'))

    def test_file_path_size_flag_and_media_path(self):
        *_, resource = make_presentation_resource()
        deck = PresentationFile(resource=resource, language='', size_bytes=11 * 1024 * 1024)
        deck.file.save('anything.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        self.assertRegex(deck.file.name, rf'^presentations/{resource.id}/[0-9a-f]{{32}}\.pptx$')
        self.assertTrue(deck.over_viewer_limit)
        self.assertEqual(deck.media_path, f'/media/{deck.file.name}')
        with override_settings(PRESENTATION_VIEWER_LIMIT_MB=20):
            self.assertFalse(deck.over_viewer_limit)

    def test_deleting_the_resource_deletes_the_file(self):
        *_, resource = make_presentation_resource()
        deck = PresentationFile(resource=resource)
        deck.file.save('x.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        path = Path(MEDIA) / deck.file.name
        self.assertTrue(path.exists())
        resource.delete()
        self.assertFalse(path.exists())

    def test_settings_defaults(self):
        from django.conf import settings
        self.assertEqual((settings.PRESENTATION_MAX_MB, settings.PRESENTATION_VIEWER_LIMIT_MB), (100, 10))
