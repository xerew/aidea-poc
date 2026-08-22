from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import OnboardingQuestion, SelfEfficacyAttempt, UserProfile
from hub.psychometrics import cronbach_alpha


class CronbachAlphaMathTests(APITestCase):
    def test_perfectly_consistent_items_give_alpha_one(self):
        # Two items that move together across 3 people → alpha = 1.0.
        self.assertEqual(cronbach_alpha([[1, 1], [2, 2], [3, 3]]), 1.0)

    def test_no_variance_returns_none(self):
        self.assertIsNone(cronbach_alpha([[3, 3], [3, 3]]))

    def test_too_few_cases_returns_none(self):
        self.assertIsNone(cronbach_alpha([[1, 2, 3, 4]]))


def _make_participants(n):
    qs = list(OnboardingQuestion.objects.filter(is_active=True).order_by('dimension__order', 'order'))
    for i in range(n):
        user = User.objects.create_user(username=f'p{i}', password='pw')
        UserProfile.objects.create(
            user=user, user_type=UserProfile.UserType.TEACHER,
            teaching_level='secondary', country='GR',
        )
        # Vary answers across people and items so columns have variance.
        answers = {str(q.id): 1 + ((i + j) % 5) for j, q in enumerate(qs)}
        SelfEfficacyAttempt.objects.create(
            user=user, answers=answers, dimension_scores={},
            overall_average=3.0, overall_band='moderate', competency_score=3,
        )
    return qs


class AdminPsychometricsEndpointTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='psy_admin', password='pw')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)

    def test_reliability_report_shape(self):
        _make_participants(8)
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse('admin-self-efficacy-psychometrics'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['n'], 8)
        self.assertIsInstance(res.data['overall_alpha'], float)
        self.assertEqual(len(res.data['dimensions']), 6)
        dim = res.data['dimensions'][0]
        self.assertIn('alpha', dim)
        self.assertEqual(len(dim['items']), 4)
        self.assertIn('item_total_r', dim['items'][0])
        # 6x6 inter-dimension correlation matrix
        self.assertEqual(len(res.data['inter_dimension']['matrix']), 6)
        self.assertEqual(len(res.data['inter_dimension']['matrix'][0]), 6)

    def test_reliability_handles_too_few_participants(self):
        _make_participants(1)
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse('admin-self-efficacy-psychometrics'))
        self.assertEqual(res.data['n'], 1)
        self.assertIsNone(res.data['overall_alpha'])

    def test_requires_admin(self):
        teacher = User.objects.create_user(username='t', password='pw')
        UserProfile.objects.create(user=teacher, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(teacher)
        self.assertEqual(
            self.client.get(reverse('admin-self-efficacy-psychometrics')).status_code, 403,
        )

    def test_research_export_is_one_row_per_participant(self):
        _make_participants(5)
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse('admin-self-efficacy-research-export'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res['Content-Type'])
        lines = res.content.decode().strip().splitlines()
        self.assertEqual(len(lines), 6)  # header + 5 participants
        header = lines[0].split(',')
        self.assertEqual(header[0], 'participant')
        self.assertIn('Q24', header)
        self.assertIn('overall_mean', header)
        self.assertTrue(lines[1].startswith('P0001,'))
