from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from hub.models import (
    AssignmentSubmission,
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)


def make_assignment_course(creator=None, slug='par1'):
    pillar = LearningPillar.objects.create(name=f'P-{slug}', slug=slug, order=1)
    course = Course.objects.create(
        title=f'C-{slug}', pillar=pillar, level='beginner', duration_hours=1,
        is_published=True, created_by=creator,
    )
    module = Module.objects.create(course=course, title='M', order=1)
    assignment = Lesson.objects.create(
        module=module, title='A', lesson_type='assignment', order=1,
        is_required=True, content='Write an essay.',
    )
    return course, module, assignment


class AssignmentModelTests(TestCase):
    def test_partner_role_exists(self):
        self.assertEqual(UserProfile.UserType.AIDEA_PARTNER, 'aidea_partner')
        self.assertEqual(UserProfile.UserType.AIDEA_PARTNER.label, 'AIDEA Partner')

    def test_submission_unique_per_user_lesson(self):
        user = User.objects.create_user(username='sub_u', password='pass12345')
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
        _, _, assignment = make_assignment_course()
        AssignmentSubmission.objects.create(user=user, lesson=assignment, text='v1')
        sub = AssignmentSubmission.objects.get(user=user, lesson=assignment)
        self.assertEqual(sub.status, AssignmentSubmission.Status.PENDING)

    def test_module_llm_toggle_default_off(self):
        _, module, _ = make_assignment_course(slug='par2')
        self.assertFalse(module.llm_review_enabled)

    def test_llm_stub_returns_none(self):
        from hub.llm_review import review_submission
        self.assertIsNone(review_submission(None))


class CompleteEndpointAssignmentGateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gate_u', password='pass12345')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.course, _, self.assignment = make_assignment_course(slug='gate1')
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def test_complete_rejects_assignment_lessons(self):
        url = f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/complete/'
        res = self.client.post(url, {'engagement_data': {'submission': 'hi'}}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('review', res.data['detail'].lower())

    def test_complete_still_works_for_text_lessons(self):
        text = Lesson.objects.create(
            module=self.assignment.module, title='T', lesson_type='text',
            order=2, is_required=True,
        )
        url = f'/api/courses/{self.course.id}/lessons/{text.id}/complete/'
        res = self.client.post(url, {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['progress_pct'], 50)  # 1 of 2 required done


class AssignmentFlowTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='flow_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.partner = User.objects.create_user(username='flow_pa', password='pass12345')
        UserProfile.objects.create(user=self.partner, user_type=UserProfile.UserType.AIDEA_PARTNER)
        self.other_creator = User.objects.create_user(username='flow_cc2', password='pass12345')
        UserProfile.objects.create(user=self.other_creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.learner = User.objects.create_user(username='flow_t', password='pass12345')
        UserProfile.objects.create(user=self.learner, user_type=UserProfile.UserType.TEACHER)

        self.course, self.module, self.assignment = make_assignment_course(self.creator, slug='flow1')
        self.enrollment = Enrollment.objects.create(user=self.learner, course=self.course)
        self.submit_url = f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/submit-assignment/'

    def _submit(self, text='My essay text'):
        self.client.force_authenticate(self.learner)
        return self.client.post(self.submit_url, {'text': text}, format='json')

    def test_submit_creates_pending_submission_without_completing(self):
        res = self._submit()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        from hub.models import LessonProgress
        self.assertFalse(LessonProgress.objects.filter(user=self.learner, lesson=self.assignment).exists())

    def test_submit_rejects_empty_and_non_assignment(self):
        res = self._submit(text='   ')
        self.assertEqual(res.status_code, 400)
        text_lesson = Lesson.objects.create(
            module=self.module, title='T', lesson_type='text', order=2,
        )
        self.client.force_authenticate(self.learner)
        res = self.client.post(
            f'/api/courses/{self.course.id}/lessons/{text_lesson.id}/submit-assignment/',
            {'text': 'x'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_lesson_detail_includes_submission(self):
        self._submit()
        res = self.client.get(f'/api/courses/{self.course.id}/lessons/{self.assignment.id}/')
        self.assertEqual(res.data['assignment_submission']['status'], 'pending')

    def test_queue_scoping(self):
        self._submit()
        self.client.force_authenticate(self.creator)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 1)
        self.client.force_authenticate(self.other_creator)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 0)
        self.client.force_authenticate(self.partner)
        self.assertEqual(len(self.client.get('/api/reviews/').data), 1)
        self.client.force_authenticate(self.learner)
        self.assertEqual(self.client.get('/api/reviews/').status_code, 403)

    def test_approve_completes_lesson_and_progress(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'approved')
        self.assertEqual(sub.reviewed_by, self.creator)
        from hub.models import LessonProgress
        lp = LessonProgress.objects.get(user=self.learner, lesson=self.assignment)
        self.assertEqual(lp.engagement_data.get('word_count'), 3)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_pct, 100)

    def test_request_changes_requires_feedback_then_resubmit(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.partner)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'request_changes', 'feedback': ''}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.client.post(
            f'/api/reviews/{sub.id}/', {'action': 'request_changes', 'feedback': 'Add sources.'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'changes_requested')

        res = self._submit(text='Better essay with sources')  # resubmit
        self.assertEqual(res.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'pending')
        self.assertEqual(sub.feedback, 'Add sources.')  # history preserved

    def test_other_creator_cannot_review_foreign_course(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.other_creator)
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_review_non_pending_rejected(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        res = self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_submit_after_approval_rejected(self):
        self._submit()
        sub = AssignmentSubmission.objects.get(user=self.learner, lesson=self.assignment)
        self.client.force_authenticate(self.creator)
        self.client.post(f'/api/reviews/{sub.id}/', {'action': 'approve'}, format='json')
        res = self._submit(text='another try')
        self.assertEqual(res.status_code, 400)
