from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import SHEET_NAMES, build_learning_workbook
from hub.models import (
    Activity,
    AIReview,
    AssignmentSubmission,
    Course,
    LearningPillar,
    Module,
    Resource,
    UserProfile,
)

from .fixtures import NOW, enroll, make_user
from .test_workbook import by_learner


class AIReviewAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = make_user('aia_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-aia', order=1)
        cls.course = Course.objects.create(title='AI', pillar=pillar, level='beginner', duration_hours=1,
                                           is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Task', order=1)
        cls.r = Resource.objects.create(activity=activity, type='assignment', order=1, title='Risks')
        cls.ann, cls.bob = make_user('ann', first='Ann'), make_user('bob', first='Bob')
        for u, verdict, human, agreed in ((cls.ann, 'approve', 'approve', True), (cls.bob, 'approve', 'changes_requested', False)):
            enroll(u, cls.course)
            sub = AssignmentSubmission.objects.create(user=u, lesson=activity, resource=cls.r, text='t',
                                                      status='approved' if human == 'approve' else 'changes_requested')
            AIReview.objects.create(submission=sub, status='done', verdict=verdict, confidence=0.9, human_verdict=human,
                                    agreed=agreed, rubric=[{'id': 'c1', 'name': 'Three risks', 'met': '', 'required': True}],
                                    criteria_results=[{'id': 'c1', 'status': 'met', 'reason': ''}],
                                    model_name='qwen2.5vl:32b', prompt_version='p1',
                                    disagreement_reason='' if agreed else 'too_lenient')

    def test_assignment_notes_include_ai_agreement(self):
        notes = content_tree(CourseData(self.course, now=NOW))['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual((notes['ai']['reviews'], notes['ai']['agreement']), (2, 0.5))
        self.assertEqual(notes['ai']['kappa'], 0.0)        # the AI approved both: no skill beyond chance

    def test_timeline_shows_ai_verdict(self):
        res = learner_timeline(CourseData(self.course, now=NOW), self.bob.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(res['ai_verdict'], 'approve')

    def test_ai_reviews_sheet(self):
        self.assertIn('AI reviews', SHEET_NAMES)
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['AI reviews'], 'Bob')
        self.assertEqual((row['AI verdict'], row['Human verdict'], row['Agreed'], row['Disagreement reason']),
                         ('approve', 'changes_requested', 'no', 'too_lenient'))
        self.assertEqual(row['Criteria'], 'c1=met')
