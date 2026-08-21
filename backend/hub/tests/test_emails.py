from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.emails import make_verify_token
from hub.models import (
    AssignmentSubmission,
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)

VALID_REGISTER = {
    'username': 'newteacher',
    'email': 'new@example.com',
    'first_name': 'New',
    'last_name': 'Teacher',
    'password': 'Str0ng!pass9',
    'confirm_password': 'Str0ng!pass9',
    'accept_terms': True,
}


class RegistrationEmailTests(APITestCase):
    def test_register_sends_welcome_and_verification(self):
        res = self.client.post(reverse('auth-register'), VALID_REGISTER, format='json')
        self.assertEqual(res.status_code, 201)
        subjects = sorted(m.subject for m in mail.outbox)
        self.assertEqual(subjects, ['Confirm your AIDEA email', 'Welcome to AIDEA'])
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])

    def test_new_account_starts_unverified(self):
        self.client.post(reverse('auth-register'), VALID_REGISTER, format='json')
        user = User.objects.get(username='newteacher')
        self.assertFalse(user.profile.email_verified)


class VerifyEmailTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', email='u1@example.com', password='pw')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.url = reverse('auth-verify-email')

    def test_valid_token_marks_verified(self):
        token = make_verify_token(self.user)
        res = self.client.post(self.url, {'token': token}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['verified'])
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.email_verified)

    def test_invalid_token_rejected(self):
        res = self.client.post(self.url, {'token': 'not-a-real-token'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.email_verified)

    def test_resend_sends_email_when_unverified(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(reverse('auth-verify-email-resend'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Confirm your AIDEA email')

    def test_resend_noop_when_already_verified(self):
        self.user.profile.email_verified = True
        self.user.profile.save()
        self.client.force_authenticate(self.user)
        self.client.post(reverse('auth-verify-email-resend'))
        self.assertEqual(len(mail.outbox), 0)


class AccessRequestEmailTests(APITestCase):
    def setUp(self):
        for name in ('admin_a', 'admin_b'):
            u = User.objects.create_user(username=name, email=f'{name}@example.com', password='pw')
            UserProfile.objects.create(user=u, user_type=UserProfile.UserType.ADMIN)
        # An admin without an email is skipped.
        noemail = User.objects.create_user(username='admin_c', password='pw')
        UserProfile.objects.create(user=noemail, user_type=UserProfile.UserType.ADMIN)
        self.teacher = User.objects.create_user(username='wants_access', email='w@example.com', password='pw')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

    def test_request_emails_all_admins_with_email(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.post(reverse('access-request'), {'message': 'I make courses.'}, format='json')
        self.assertEqual(res.status_code, 201)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['admin_a@example.com', 'admin_b@example.com'])
        self.assertIn('access request', mail.outbox[0].subject.lower())


class AssignmentReviewedEmailTests(APITestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(username='rev', password='pw')
        UserProfile.objects.create(user=self.reviewer, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = User.objects.create_user(username='stu', email='stu@example.com', password='pw')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

        pillar = LearningPillar.objects.create(name='P', slug='pe', order=1)
        self.course = Course.objects.create(
            title='C', pillar=pillar, level='beginner', duration_hours=1, created_by=self.reviewer,
        )
        module = Module.objects.create(course=self.course, title='M', order=1)
        self.lesson = Lesson.objects.create(module=module, title='HW', lesson_type='assignment', order=1)
        Enrollment.objects.create(user=self.teacher, course=self.course)
        self.submission = AssignmentSubmission.objects.create(
            user=self.teacher, lesson=self.lesson, text='my work',
            status=AssignmentSubmission.Status.PENDING,
        )

    def test_request_changes_emails_the_submitter(self):
        self.client.force_authenticate(self.reviewer)
        res = self.client.post(
            reverse('review-action', kwargs={'pk': self.submission.pk}),
            {'action': 'request_changes', 'feedback': 'Please expand section 2.'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['stu@example.com'])
        self.assertIn('review', mail.outbox[0].subject.lower())
