from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase  # noqa: F401  (used by later tasks)

from hub.models import (
    AssignmentSubmission,
    Course,
    Enrollment,  # noqa: F401
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
