from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import AccessRequest, UserProfile


def make_user(username, user_type, password='pass1234'):
    u = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    UserProfile.objects.create(user=u, user_type=user_type, avatar_initials=username[:2].upper())
    return u


class AccessRequestMineTest(APITestCase):
    def setUp(self):
        self.teacher = make_user('t1', UserProfile.UserType.TEACHER)

    def test_mine_returns_null_when_no_request(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/access-requests/mine/')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data)

    def test_mine_returns_latest_request(self):
        req = AccessRequest.objects.create(user=self.teacher, message='I want access')
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/access-requests/mine/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], req.id)
        self.assertEqual(res.data['status'], 'pending')


class AccessRequestSubmitTest(APITestCase):
    def setUp(self):
        self.teacher = make_user('t2', UserProfile.UserType.TEACHER)

    def test_submit_creates_pending_request(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.post('/api/access-requests/', {'message': 'I want to create courses'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        self.assertTrue(AccessRequest.objects.filter(user=self.teacher).exists())

    def test_second_submit_while_pending_returns_400(self):
        AccessRequest.objects.create(user=self.teacher, message='First request')
        self.client.force_authenticate(self.teacher)
        res = self.client.post('/api/access-requests/', {'message': 'Second request'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_non_teacher_can_submit_request(self):
        # #7: the role gate was dropped — any user without creator/admin access may request.
        partner = make_user('partner1', UserProfile.UserType.AIDEA_PARTNER)
        self.client.force_authenticate(partner)
        res = self.client.post('/api/access-requests/', {'message': 'I want to author'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(AccessRequest.objects.filter(user=partner).exists())

    def test_content_creator_cannot_submit_request(self):
        creator = make_user('cc1', UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(creator)
        res = self.client.post('/api/access-requests/', {'message': 'redundant'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AccessRequest.objects.filter(user=creator).exists())

    def test_cancel_pending_request(self):
        req = AccessRequest.objects.create(user=self.teacher, message='Cancel me')
        req_id = req.id
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(f'/api/access-requests/{req_id}/')
        self.assertEqual(res.status_code, 204)
        # row was deleted (not status-updated)
        with self.assertRaises(AccessRequest.DoesNotExist):
            req.refresh_from_db()
        self.assertFalse(AccessRequest.objects.filter(pk=req_id).exists())

    def test_cannot_cancel_approved_request(self):
        req = AccessRequest.objects.create(
            user=self.teacher, message='Already approved', status=AccessRequest.Status.APPROVED,
        )
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(f'/api/access-requests/{req.id}/')
        self.assertEqual(res.status_code, 400)


class AdminAccessRequestReviewTest(APITestCase):
    def setUp(self):
        self.admin   = make_user('adm1', UserProfile.UserType.ADMIN)
        self.teacher = make_user('t3',   UserProfile.UserType.TEACHER)
        self.req = AccessRequest.objects.create(user=self.teacher, message='Please approve me')

    def test_admin_approves_request_and_promotes_user(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/access-requests/{self.req.id}/',
            {'action': 'approve'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'approved')
        self.teacher.profile.refresh_from_db()
        self.assertEqual(self.teacher.profile.user_type, 'content_creator')

    def test_admin_denies_request_with_reason(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/access-requests/{self.req.id}/',
            {'action': 'deny', 'denial_reason': 'Not enough courses planned.'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'denied')
        self.assertEqual(self.req.denial_reason, 'Not enough courses planned.')
        self.assertFalse(self.req.denial_seen)

    def test_teacher_dismisses_denial(self):
        self.req.status = AccessRequest.Status.DENIED
        self.req.denial_reason = 'Not ready'
        self.req.save()
        self.client.force_authenticate(self.teacher)
        res = self.client.patch(f'/api/access-requests/{self.req.id}/seen/')
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertTrue(self.req.denial_seen)
