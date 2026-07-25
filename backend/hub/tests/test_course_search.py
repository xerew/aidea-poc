from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile


class CourseSearchTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(username='search_t', password='pass12345')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(user)
        pillar = LearningPillar.objects.create(name='P', slug='p-search', order=1)
        Course.objects.create(
            title='Prompt Engineering', description='Craft effective prompts.',
            pillar=pillar, is_published=True,
        )
        Course.objects.create(
            title='Classroom Basics', description='Uses prompting techniques too.',
            pillar=pillar, is_published=True,
        )
        Course.objects.create(
            title='Unrelated', description='Nothing here.', pillar=pillar, is_published=True,
        )
        self.url = reverse('courses')

    def _titles(self, q):
        res = self.client.get(self.url, {'search': q})
        return {c['title'] for c in res.data}

    def test_search_matches_title(self):
        self.assertEqual(self._titles('prompt engineering'), {'Prompt Engineering'})

    def test_search_matches_description(self):
        # "prompt" appears in one title and one description.
        self.assertEqual(self._titles('prompt'), {'Prompt Engineering', 'Classroom Basics'})

    def test_search_is_case_insensitive_and_partial(self):
        self.assertEqual(self._titles('CRAFT'), {'Prompt Engineering'})

    def test_search_no_match(self):
        self.assertEqual(self._titles('zzzzz'), set())
