from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    CompetencyChange,
    Course,
    Enrollment,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)


class ActivityCompleteResourcesTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('acr_u', password='x')
        UserProfile.objects.create(user=self.user, competency_score=0)
        pillar = LearningPillar.objects.get_or_create(slug='p-acr', defaults={'name': 'P', 'order': 1})[0]
        self.course = Course.objects.create(title='C', pillar=pillar, level='beginner', duration_hours=1, is_published=True)
        module = Module.objects.create(course=self.course, title='M', order=1)
        self.activity = Activity.objects.create(module=module, title='A', order=1)
        make = lambda kind, order, **kw: Resource.objects.create(activity=self.activity, type=kind, order=order, **kw)  # noqa: E731
        self.text = make('text', 1, content='<p>Hi</p>')
        self.image = make('image', 2, url='https://x/a.png')
        self.optional_pdf = make('pdf', 3, url='https://x/a.pdf', is_required=False)
        self.h5p_self = make('h5p', 4, h5p_self_complete=True)
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.url = reverse('activity-complete-resources', kwargs={'pk': self.course.id, 'lesson_pk': self.activity.id})
        self.client.force_authenticate(self.user)

    def done_ids(self):
        return set(ResourceProgress.objects.filter(user=self.user, completed_at__isnull=False)
                   .values_list('resource_id', flat=True))

    def test_completes_all_self_completed_resources_and_the_course(self):
        res = self.client.post(self.url, {'scroll_pct': 80}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(set(res.data['completed_resource_ids']), {self.text.id, self.image.id, self.optional_pdf.id, self.h5p_self.id})
        self.assertEqual((res.data['activity_completed'], res.data['progress_pct']), (True, 100))
        self.assertEqual(ResourceProgress.objects.get(user=self.user, resource=self.text).engagement_data.get('scroll_pct'), 80)
        self.assertEqual(CompetencyChange.objects.filter(user=self.user).count(), 1)

    def test_second_call_changes_nothing(self):
        self.client.post(self.url, {}, format='json')
        res = self.client.post(self.url, {}, format='json')
        self.assertEqual(res.data['completed_resource_ids'], [])
        self.assertEqual(CompetencyChange.objects.filter(user=self.user).count(), 1)

    def test_quiz_is_not_completed_by_the_button(self):
        quiz = Resource.objects.create(activity=self.activity, type='quiz', order=5,
                                       quiz_data=[{'question': 'Q', 'options': [{'text': 'A', 'is_correct': True}]}])
        scoring_h5p = Resource.objects.create(activity=self.activity, type='h5p', order=6)
        assignment = Resource.objects.create(activity=self.activity, type='assignment', order=7, instructions='Do')
        res = self.client.post(self.url, {}, format='json')
        self.assertNotIn(quiz.id, self.done_ids())
        self.assertNotIn(scoring_h5p.id, self.done_ids())
        self.assertNotIn(assignment.id, self.done_ids())
        self.assertEqual(res.data['activity_completed'], False)

    def test_not_enrolled_and_wrong_activity(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).delete()
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 403)
        Enrollment.objects.create(user=self.user, course=self.course)
        other = reverse('activity-complete-resources', kwargs={'pk': self.course.id, 'lesson_pk': 999999})
        self.assertEqual(self.client.post(other, {}, format='json').status_code, 404)
