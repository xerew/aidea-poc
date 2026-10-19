import tempfile

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase, override_settings

from hub.models import PresentationFile, UserProfile
from hub.serializers.content import ResourceLearnSerializer

from .test_presentation_models import make_presentation_resource

MEDIA = tempfile.mkdtemp(prefix='aidea-pres-learn-')


@override_settings(MEDIA_ROOT=MEDIA, MEDIA_URL='/media/')
class LearnerPresentationTests(TestCase):
    def setUp(self):
        *_, self.resource = make_presentation_resource()
        self.user = User.objects.create_user('pres_learner', password='x')
        UserProfile.objects.create(user=self.user, language='el')

    def add(self, language, size=1000, title='Deck'):
        deck = PresentationFile(resource=self.resource, language=language, title=title, slide_count=5, size_bytes=size)
        deck.file.save('d.pptx', ContentFile(b'PK'), save=False)
        deck.save()
        return deck

    def payload(self):
        request = RequestFactory().get('/')          # host 'testserver' (allowed in tests)
        request.user = self.user
        return ResourceLearnSerializer(self.resource, context={'request': request}).data['presentation']

    def test_viewers_language_wins(self):
        self.add('')
        el = self.add('el', title='Διαφάνειες')
        p = self.payload()
        self.assertEqual((p['language'], p['title'], p['slides']), ('el', 'Διαφάνειες', 5))
        self.assertEqual(p['url'], f'http://testserver/media/{el.file.name}')

    def test_falls_back_to_main_deck(self):
        self.add('')
        self.add('fr')
        self.assertEqual(self.payload()['language'], '')

    def test_no_deck_gives_null(self):
        self.add('fr')
        self.assertIsNone(self.payload())

    def test_download_flag_and_forced_download_over_limit(self):
        self.add('')
        self.assertFalse(self.payload()['downloadable'])
        self.resource.presentation_downloadable = True
        self.resource.save()
        self.assertTrue(self.payload()['downloadable'])
        self.resource.presentation_downloadable = False
        self.resource.save()
        PresentationFile.objects.filter(resource=self.resource).update(size_bytes=50 * 1024 * 1024)
        p = self.payload()
        self.assertEqual((p['over_viewer_limit'], p['downloadable']), (True, True))

    def test_other_types_have_no_presentation(self):
        self.resource.type = 'pdf'
        self.resource.save()
        self.assertIsNone(self.payload())
