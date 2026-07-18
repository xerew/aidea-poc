from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import PreferenceOption, PreferenceQuestion, UserProfile


class PreferenceQuizModelTests(TestCase):
    def test_question_option_roundtrip(self):
        q = PreferenceQuestion.objects.create(text='Q1?', order=1)
        PreferenceOption.objects.create(question=q, text='Watch', maps_to='video', order=1)
        PreferenceOption.objects.create(question=q, text='Read', maps_to='text', order=2)
        self.assertEqual(list(q.options.values_list('maps_to', flat=True)), ['video', 'text'])

    def test_seed_is_idempotent(self):
        from hub.management.commands.seed_data.preference_quiz import seed_preference_quiz
        seed_preference_quiz()
        first_count = PreferenceQuestion.objects.count()
        self.assertGreaterEqual(first_count, 4)
        seed_preference_quiz()
        self.assertEqual(PreferenceQuestion.objects.count(), first_count)
        for question in PreferenceQuestion.objects.all():
            self.assertEqual(question.options.count(), 4)
            self.assertEqual(
                sorted(question.options.values_list('maps_to', flat=True)),
                sorted(['video', 'text', 'visual', 'interactive']),
            )


class PreferenceQuizApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pref_user', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.q1 = PreferenceQuestion.objects.create(text='Q1?', order=1)
        self.q2 = PreferenceQuestion.objects.create(text='Q2?', order=2)
        self.inactive = PreferenceQuestion.objects.create(text='Old?', order=3, is_active=False)
        self.q1_video = PreferenceOption.objects.create(question=self.q1, text='a', maps_to='video', order=1)
        self.q1_text  = PreferenceOption.objects.create(question=self.q1, text='b', maps_to='text', order=2)
        self.q2_video = PreferenceOption.objects.create(question=self.q2, text='c', maps_to='video', order=1)
        self.q2_visual = PreferenceOption.objects.create(question=self.q2, text='d', maps_to='visual', order=2)
        PreferenceOption.objects.create(question=self.inactive, text='e', maps_to='text', order=1)
        self.url = '/api/preference-quiz/'
        self.client.force_authenticate(self.user)

    def test_get_returns_active_questions_without_maps_to(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([q['text'] for q in res.data], ['Q1?', 'Q2?'])
        self.assertNotIn('maps_to', res.data[0]['options'][0])

    def test_post_saves_winner(self):
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q2.id, 'option_id': self.q2_video.id},
        ]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['learning_style'], 'video')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.learning_style, 'video')

    def test_tie_breaks_toward_declaration_order(self):
        # one video vote, one visual vote -> video wins (declared first)
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q2.id, 'option_id': self.q2_visual.id},
        ]}, format='json')
        self.assertEqual(res.data['learning_style'], 'video')

    def test_invalid_option_rejected(self):
        res = self.client.post(self.url, {'answers': [{'question_id': self.q1.id, 'option_id': 999999}]}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_two_answers_for_same_question_rejected(self):
        res = self.client.post(self.url, {'answers': [
            {'question_id': self.q1.id, 'option_id': self.q1_video.id},
            {'question_id': self.q1.id, 'option_id': self.q1_text.id},
        ]}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_empty_answers_rejected(self):
        res = self.client.post(self.url, {'answers': []}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
