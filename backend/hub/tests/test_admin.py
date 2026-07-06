from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import UserProfile


def make_user(username, user_type, password='pass1234'):
    u = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    UserProfile.objects.create(user=u, user_type=user_type, avatar_initials=username[:2].upper())
    return u


class AdminUserListTest(APITestCase):
    def setUp(self):
        self.admin  = make_user('admin1',   UserProfile.UserType.ADMIN)
        self.teacher = make_user('teacher1', UserProfile.UserType.TEACHER)

    def test_non_admin_cannot_list_users(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/admin/users/')
        self.assertEqual(res.status_code, 403)

    def test_admin_lists_all_users(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/admin/users/')
        self.assertEqual(res.status_code, 200)
        ids = [u['id'] for u in res.data]
        self.assertIn(self.admin.id, ids)
        self.assertIn(self.teacher.id, ids)
        self.assertIn('user_type', res.data[0])
        self.assertIn('avatar_initials', res.data[0])


class AdminUserRoleTest(APITestCase):
    def setUp(self):
        self.admin   = make_user('admin2',   UserProfile.UserType.ADMIN)
        self.teacher = make_user('teacher2', UserProfile.UserType.TEACHER)

    def test_admin_changes_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.teacher.id}/role/',
            {'user_type': 'content_creator'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.teacher.profile.refresh_from_db()
        self.assertEqual(self.teacher.profile.user_type, 'content_creator')

    def test_admin_cannot_change_own_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.admin.id}/role/',
            {'user_type': 'teacher'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_invalid_role_returns_400(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.teacher.id}/role/',
            {'user_type': 'superuser'}, format='json',
        )
        self.assertEqual(res.status_code, 400)
