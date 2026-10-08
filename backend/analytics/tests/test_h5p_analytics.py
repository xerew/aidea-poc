from datetime import timedelta

from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import build_learning_workbook
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile

from .fixtures import NOW, add_event, complete, enroll, make_user
from .test_workbook import by_learner


def at(minute):
    return NOW - timedelta(minutes=60 - minute)


class H5PAnalyticsTests(TestCase):
    """ann: Q1 ✓, Q2 ✗ → attempt 1 (8/10); Q1 ✓ → attempt 2 (10/10); Q1 ✗ (unfinished)
    bob: Q1 ✗, Q2 ✗ → attempt 1 (4/10) — first score 0.4 → stuck
    cat: enrolled, nothing yet"""

    @classmethod
    def setUpTestData(cls):
        creator = make_user('h5pa_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-h5pa', order=1)
        cls.course = Course.objects.create(title='H5P', pillar=pillar, level='beginner',
                                           duration_hours=1, is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Practice', order=1)
        cls.r = Resource.objects.create(activity=activity, type='h5p', order=1, title='Drag task')
        cls.ann, cls.bob, cls.cat = make_user('ann', first='Ann'), make_user('bob', first='Bob'), make_user('cat', first='Cat')
        for u in (cls.ann, cls.bob, cls.cat):
            enroll(u, cls.course)
        r = cls.r
        add_event(cls.ann, r, 'h5p_answer', at=at(1), question='Q1', correct=True, raw=1, max=1, seconds=4)
        add_event(cls.ann, r, 'h5p_answer', at=at(2), question='Q2', correct=False, raw=0, max=1, seconds=6)
        add_event(cls.ann, r, 'h5p_attempt', at=at(3), raw=8, max=10, success=True, duration_s=30, language='')
        add_event(cls.ann, r, 'h5p_answer', at=at(4), question='Q1', correct=True, raw=1, max=1, seconds=2)
        add_event(cls.ann, r, 'h5p_attempt', at=at(5), raw=10, max=10, success=True, duration_s=12, language='')
        add_event(cls.ann, r, 'h5p_answer', at=at(6), question='Q1', correct=False, raw=0, max=1, seconds=1)
        complete(cls.ann, r, at=at(3), quiz_score=0.8, engagement_data={'h5p': {'raw': 8, 'max': 10}})
        add_event(cls.bob, r, 'h5p_answer', at=at(1), question='Q1', correct=False, raw=0, max=1, seconds=9)
        add_event(cls.bob, r, 'h5p_answer', at=at(2), question='Q2', correct=False, raw=0, max=1, seconds=9)
        add_event(cls.bob, r, 'h5p_attempt', at=at(3), raw=4, max=10, success=False, duration_s=40, language='el')
        complete(cls.bob, r, at=at(3), quiz_score=0.4, engagement_data={'h5p': {'raw': 4, 'max': 10}})

    def setUp(self):
        self.cd = CourseData(self.course, now=NOW)

    def test_attempts_numbered_by_time(self):
        attempts = self.cd.h5p_attempts(self.ann.id, self.r)
        self.assertEqual([(a['number'], a['raw']) for a in attempts], [(1, 8), (2, 10)])

    def test_answers_belong_to_their_attempt(self):
        answers = self.cd.h5p_answers(self.ann.id, self.r)
        self.assertEqual([(a['attempt'], a['question'], a['correct']) for a in answers],
                         [(1, 'Q1', True), (1, 'Q2', False), (2, 'Q1', True), (3, 'Q1', False)])

    def test_notes(self):
        notes = content_tree(self.cd)['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual(notes, {
            'finished': 2, 'avg_score_pct': 60, 'avg_attempts': 1.5,
            'hardest_question': {'question': 'Q2', 'pct_correct': 0},
        })

    def test_low_first_score_is_stuck(self):
        status = {e.user.username: self.cd.status(e) for e in self.cd.enrollments}
        self.assertEqual(status, {'ann': 'on_track', 'bob': 'stuck', 'cat': 'on_track'})

    def test_detail_and_timeline(self):
        detail = self.cd.resource_detail(self.ann.id, self.r)
        self.assertEqual((detail['quiz_score'], detail['h5p_attempts']), (0.8, 2))
        res = learner_timeline(self.cd, self.ann.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual((len(res['h5p']['attempts']), len(res['h5p']['answers'])), (2, 4))
        cat = learner_timeline(self.cd, self.cat.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(cat['h5p'], {'attempts': [], 'answers': []})

    def test_workbook(self):
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['Resources'], 'Ann')
        self.assertEqual((row['Score %'], row['H5P attempts']), (80, 2))
        answers = by_learner(wb['H5P answers'], 'Ann')
        self.assertEqual([(a['Attempt #'], a['Question'], a['Right']) for a in answers],
                         [(1, 'Q1', 'yes'), (1, 'Q2', 'no'), (2, 'Q1', 'yes'), (3, 'Q1', 'no')])
        first = by_learner(wb['Events'], 'Bob')[0]
        self.assertIn('"question": "Q1"', first['Data'])


class H5PAttemptBoundaryTests(TestCase):
    """dan answers Q1 in one page visit and leaves; next visit he answers Q1, Q2
    and finishes. The abandoned answer is attempt 1 (unfinished); the finished
    attempt is number 2 with only that visit's answers."""

    def test_unfinished_visit_is_its_own_attempt(self):
        import uuid

        from hub.models import LearningEvent

        from .fixtures import add_visit
        creator = make_user('h5pb_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-h5pb', order=1)
        course = Course.objects.create(title='B', pillar=pillar, level='beginner', duration_hours=1,
                                       is_published=True, created_by=creator)
        module = Module.objects.create(course=course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='A', order=1)
        r = Resource.objects.create(activity=activity, type='h5p', order=1)
        dan = make_user('dan', first='Dan')
        enroll(dan, course)
        first, second = add_visit(dan, r, start=at(0)), add_visit(dan, r, start=at(10))

        def event(kind, minute, visit, **data):
            LearningEvent.objects.create(user=dan, resource=r, course=course, visit=visit,
                                         event_key=uuid.uuid4(), event_type=kind, occurred_at=at(minute), data=data)
        event('h5p_answer', 1, first, question='Q1', correct=False)
        event('h5p_answer', 11, second, question='Q1', correct=True)
        event('h5p_answer', 12, second, question='Q2', correct=True)
        event('h5p_attempt', 13, second, raw=2, max=2)

        cd = CourseData(course, now=NOW)
        self.assertEqual([(a['attempt'], a['question']) for a in cd.h5p_answers(dan.id, r)],
                         [(1, 'Q1'), (2, 'Q1'), (2, 'Q2')])
        self.assertEqual([(a['number'], a['raw']) for a in cd.h5p_attempts(dan.id, r)], [(2, 2)])
