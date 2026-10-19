from django.test import TestCase

from analytics.learning import CourseData, content_tree, learner_timeline
from analytics.workbook import build_learning_workbook
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile

from .fixtures import NOW, add_event, enroll, make_user
from .test_workbook import by_learner


class PresentationAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = make_user('pa_cc', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-pa', order=1)
        cls.course = Course.objects.create(title='Decks', pillar=pillar, level='beginner', duration_hours=1,
                                           is_published=True, created_by=creator)
        module = Module.objects.create(course=cls.course, title='M', order=1)
        activity = Activity.objects.create(module=module, title='Slides', order=1)
        cls.r = Resource.objects.create(activity=activity, type='presentation', order=1, title='Week 1')
        cls.ann, cls.bob = make_user('ann', first='Ann'), make_user('bob', first='Bob')
        for u in (cls.ann, cls.bob):
            enroll(u, cls.course)
        add_event(cls.ann, cls.r, 'presentation_download')

    def test_notes_count_downloads(self):
        notes = content_tree(CourseData(self.course, now=NOW))['modules'][0]['activities'][0]['resources'][0]['notes']
        self.assertEqual(notes, {'downloaded': 1})

    def test_timeline_detail(self):
        cd = CourseData(self.course, now=NOW)
        res = learner_timeline(cd, self.ann.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(res['presentation_downloaded'], 1)

    def test_resources_sheet_column(self):
        wb = build_learning_workbook([self.course], now=NOW)
        [row] = by_learner(wb['Resources'], 'Ann')
        self.assertEqual(row['Presentation downloaded'], 1)
        self.assertEqual(row['Type'], 'presentation')
