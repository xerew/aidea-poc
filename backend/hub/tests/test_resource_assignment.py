from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    AssignmentSubmission,
    Course,
    Enrollment,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)


class ResourceAssignmentTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='x')
        UserProfile.objects.create(user=self.author, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.learner = User.objects.create_user(username='learner', password='x')
        UserProfile.objects.create(user=self.learner, user_type=UserProfile.UserType.TEACHER)

        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar, is_published=True, created_by=self.author)
        module = Module.objects.create(title='M', course=self.course, order=1)
        self.activity = Activity.objects.create(module=module, title='A', order=1)
        self.res = Resource.objects.create(
            activity=self.activity, type='assignment', order=1, instructions='do it',
        )
        Enrollment.objects.create(user=self.learner, course=self.course)

    def _submit_url(self):
        return reverse('resource-submit-assignment', kwargs={
            'pk': self.course.pk, 'lesson_pk': self.activity.pk, 'resource_pk': self.res.pk})

    def test_submit_to_resource(self):
        self.client.force_authenticate(self.learner)
        res = self.client.post(self._submit_url(), {'text': 'my answer'}, format='json')
        self.assertEqual(res.status_code, 201)
        sub = AssignmentSubmission.objects.get(user=self.learner, resource=self.res)
        self.assertEqual(sub.status, 'pending')

    def test_review_approve_completes_resource(self):
        self.client.force_authenticate(self.learner)
        self.client.post(self._submit_url(), {'text': 'answer'}, format='json')
        sub = AssignmentSubmission.objects.get(user=self.learner, resource=self.res)

        self.client.force_authenticate(self.author)
        res = self.client.post(reverse('review-action', kwargs={'pk': sub.pk}),
                               {'action': 'approve'}, format='json')
        self.assertEqual(res.status_code, 200)
        rp = ResourceProgress.objects.get(user=self.learner, resource=self.res)
        self.assertIsNotNone(rp.completed_at)
