from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile


def make_user(username, user_type):
    u = User.objects.create_user(username=username, password='pass12345')
    UserProfile.objects.create(user=u, user_type=user_type)
    return u


class AdminRecomputeTests(APITestCase):
    def setUp(self):
        self.admin = make_user('rec_admin', UserProfile.UserType.ADMIN)
        self.teacher = make_user('rec_teacher', UserProfile.UserType.TEACHER)
        self.url = reverse('admin-recompute-recommendations')

    @patch('hub.tasks.recompute_all_recommendations.delay')
    def test_admin_queues_recompute(self, mock_delay):
        self.client.force_authenticate(self.admin)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with()

    @patch('hub.tasks.recompute_all_recommendations.delay')
    def test_non_admin_forbidden(self, mock_delay):
        self.client.force_authenticate(self.teacher)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        mock_delay.assert_not_called()

    def test_unauthenticated_rejected(self):
        self.assertEqual(self.client.post(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
