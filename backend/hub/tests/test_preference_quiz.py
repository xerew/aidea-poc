from django.test import TestCase
from rest_framework.test import APITestCase  # noqa: F401  (used by Task 2 classes)

from hub.models import PreferenceOption, PreferenceQuestion, UserProfile  # noqa: F401


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
