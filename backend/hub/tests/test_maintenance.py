from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from hub.models import MaintenanceNotice, UserProfile


class MaintenanceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='m_admin', password='pw')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)
        self.teacher = User.objects.create_user(username='m_teacher', password='pw')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

    def test_public_inactive_by_default(self):
        res = self.client.get(reverse('maintenance'))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['active'])

    def test_admin_sets_and_public_sees_active_window(self):
        start = (timezone.now() + timedelta(hours=1)).isoformat()
        end = (timezone.now() + timedelta(hours=3)).isoformat()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(reverse('admin-maintenance'), {
            'enabled': True, 'message': 'Platform update', 'starts_at': start, 'ends_at': end,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['enabled'])

        self.client.force_authenticate(None)
        pub = self.client.get(reverse('maintenance'))
        self.assertTrue(pub.data['active'])
        self.assertEqual(pub.data['message'], 'Platform update')
        self.assertIsNotNone(pub.data['starts_at'])
        self.assertIsNotNone(pub.data['ends_at'])

    def test_auto_hides_after_window_ends(self):
        cfg = MaintenanceNotice.get()
        cfg.enabled = True
        cfg.starts_at = timezone.now() - timedelta(hours=3)
        cfg.ends_at = timezone.now() - timedelta(hours=1)  # already over
        cfg.save()
        res = self.client.get(reverse('maintenance'))
        self.assertFalse(res.data['active'])

    def test_disabling_hides_it(self):
        cfg = MaintenanceNotice.get()
        cfg.enabled = True
        cfg.ends_at = timezone.now() + timedelta(hours=2)
        cfg.save()
        self.assertTrue(self.client.get(reverse('maintenance')).data['active'])
        self.client.force_authenticate(self.admin)
        self.client.patch(reverse('admin-maintenance'), {'enabled': False}, format='json')
        self.client.force_authenticate(None)
        self.assertFalse(self.client.get(reverse('maintenance')).data['active'])

    def test_admin_endpoint_requires_admin(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(reverse('admin-maintenance')).status_code, 403)
        self.assertEqual(
            self.client.patch(reverse('admin-maintenance'), {'enabled': True}, format='json').status_code, 403,
        )
