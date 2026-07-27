from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import Feedback, UserProfile


def make_user(username, role):
    u = User.objects.create_user(username=username, password='pass12345',
                                 first_name=username.title(), last_name='X')
    UserProfile.objects.create(user=u, user_type=role, avatar_initials='XX')
    return u


class FeedbackTests(APITestCase):
    def setUp(self):
        self.teacher = make_user('t1', UserProfile.UserType.TEACHER)
        self.creator = make_user('c1', UserProfile.UserType.CONTENT_CREATOR)
        self.partner = make_user('p1', UserProfile.UserType.AIDEA_PARTNER)
        self.admin = make_user('a1', UserProfile.UserType.ADMIN)

    def _submit(self, user, category='bug', message='Something broke', attachments=None):
        self.client.force_authenticate(user)
        payload = {'category': category, 'message': message}
        if attachments is not None:
            payload['attachments'] = attachments
        return self.client.post('/api/feedback/', payload, format='json')

    def test_teacher_submission_goes_to_user_stream(self):
        res = self._submit(self.teacher)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['stream'], 'user')
        self.assertEqual(res.data['status'], 'new')

    def test_creator_submission_is_user_stream(self):
        res = self._submit(self.creator, category='suggestion')
        self.assertEqual(res.data['stream'], 'user')

    def test_partner_submission_goes_to_partner_stream(self):
        res = self._submit(self.partner, category='feature_request')
        self.assertEqual(res.data['stream'], 'partner')

    def test_invalid_category_rejected(self):
        res = self._submit(self.teacher, category='nonsense')
        self.assertEqual(res.status_code, 400)

    def test_empty_message_rejected(self):
        res = self._submit(self.teacher, message='   ')
        self.assertEqual(res.status_code, 400)

    def test_attachments_stored(self):
        att = [{'type': 'link', 'url': 'https://youtu.be/x', 'name': 'demo'}]
        res = self._submit(self.teacher, attachments=att)
        self.assertEqual(res.data['attachments'], att)

    def test_mine_returns_own_only(self):
        self._submit(self.teacher)
        self._submit(self.partner)
        self.client.force_authenticate(self.teacher)
        rows = self.client.get('/api/feedback/mine/').data
        self.assertEqual(len(rows), 1)

    def test_admin_list_sees_all_streams(self):
        self._submit(self.teacher)
        self._submit(self.partner)
        self.client.force_authenticate(self.admin)
        rows = self.client.get('/api/admin/feedback/').data
        self.assertEqual(len(rows), 2)

    def test_non_admin_cannot_list(self):
        self.client.force_authenticate(self.partner)
        self.assertEqual(self.client.get('/api/admin/feedback/').status_code, 403)

    def test_admin_sets_status(self):
        self._submit(self.teacher)
        fb = Feedback.objects.first()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(f'/api/admin/feedback/{fb.id}/', {'status': 'resolved'}, format='json')
        self.assertEqual(res.status_code, 200)
        fb.refresh_from_db()
        self.assertEqual(fb.status, 'resolved')
        self.assertEqual(fb.reviewed_by, self.admin)

    def test_reject_requires_reason(self):
        self._submit(self.teacher)
        fb = Feedback.objects.first()
        self.client.force_authenticate(self.admin)
        res = self.client.patch(f'/api/admin/feedback/{fb.id}/', {'status': 'rejected'}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.patch(
            f'/api/admin/feedback/{fb.id}/',
            {'status': 'rejected', 'rejection_reason': 'Not a bug'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        fb.refresh_from_db()
        self.assertEqual(fb.rejection_reason, 'Not a bug')

    def test_non_admin_cannot_set_status(self):
        self._submit(self.teacher)
        fb = Feedback.objects.first()
        self.client.force_authenticate(self.partner)
        res = self.client.patch(f'/api/admin/feedback/{fb.id}/', {'status': 'resolved'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_submit_requires_auth(self):
        self.client.force_authenticate(None)
        res = self.client.post('/api/feedback/', {'category': 'bug', 'message': 'x'}, format='json')
        self.assertEqual(res.status_code, 401)
