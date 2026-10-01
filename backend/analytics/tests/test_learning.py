from django.test import TestCase

from analytics.learning import (
    CourseData,
    content_tree,
    learner_row,
    learner_timeline,
    time_summary,
)
from hub.models import ResourceVisit

from .fixtures import NOW, CourseFixture


class LearningAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.f = CourseFixture()

    def setUp(self):
        self.cd = CourseData(self.f.course, now=NOW)

    def node(self, tree, *path):
        """Walk the content tree by ids: module, activity, resource."""
        node = next(m for m in tree['modules'] if m['id'] == path[0])
        if len(path) > 1:
            node = next(a for a in node['activities'] if a['id'] == path[1])
        if len(path) > 2:
            node = next(r for r in node['resources'] if r['id'] == path[2])
        return node

    def test_time_summary_counts_page_visits_once(self):
        t = time_summary(ResourceVisit.objects.filter(user=self.f.ada))
        self.assertEqual((t['active_s'], t['visible_s'], t['visits']), (350, 390, 2))

    def test_statuses(self):
        status = {e.user.username: self.cd.status(e) for e in self.cd.enrollments}
        self.assertEqual(status, {
            'ada': 'on_track', 'bo': 'completed', 'cy': 'inactive',
            'di': 'stuck', 'ev': 'stuck', 'old': 'on_track',
        })

    def test_text_resource_stats(self):
        f = self.f
        stats = self.node(content_tree(self.cd), f.m1.id, f.a1.id, f.text.id)['stats']
        # Reached by ada, bo (visits) and old (progress only); median over measured.
        self.assertEqual(stats, {'reached': 3, 'done': 3, 'median_active_s': 225, 'mean_active_s': 225, 'dropped': 0})

    def test_video_resource_stats_and_notes(self):
        f = self.f
        node = self.node(content_tree(self.cd), f.m1.id, f.a1.id, f.video.id)
        self.assertEqual(node['stats'], {'reached': 4, 'done': 1, 'median_active_s': 60, 'mean_active_s': 97, 'dropped': 1})
        self.assertEqual(node['notes'], {'avg_watched_pct': 25, 'typical_stop_s': 75})

    def test_quiz_notes(self):
        f = self.f
        node = self.node(content_tree(self.cd), f.m1.id, f.a2.id, f.quiz.id)
        self.assertIsNone(node['stats']['median_active_s'])  # reached, but never measured
        self.assertEqual(node['notes'], {
            'avg_score_pct': 50,
            'hardest_question': {'number': 1, 'question': 'Q one', 'pct_correct': 50},
            'avg_seconds_per_question': 16.7,
        })

    def test_pdf_and_assignment_notes(self):
        f = self.f
        tree = content_tree(self.cd)
        self.assertEqual(self.node(tree, f.m2.id, f.a3.id, f.pdf.id)['notes'], {'opened': 1, 'downloaded': 1})
        self.assertEqual(
            self.node(tree, f.m2.id, f.a3.id, f.assign.id)['notes'],
            {'submitted': 1, 'approved': 1, 'waiting': 0, 'changes_requested': 0},
        )

    def test_activity_and_module_aggregate_children(self):
        f = self.f
        tree = content_tree(self.cd)
        self.assertEqual(self.node(tree, f.m1.id, f.a1.id)['stats'],
                         {'reached': 5, 'done': 1, 'median_active_s': 180, 'mean_active_s': 185, 'dropped': 1})
        m1 = self.node(tree, f.m1.id)['stats']
        self.assertEqual((m1['reached'], m1['done'], m1['dropped']), (6, 1, 1))
        self.assertEqual(tree['learners'], 6)

    def test_learner_row(self):
        row = learner_row(self.cd, self.f.ada_enr)
        self.assertEqual((row['active_s'], row['visible_s'], row['visits']), (350, 390, 2))
        self.assertEqual(row['position']['resource_id'], self.f.text.id)
        self.assertEqual(row['status'], 'on_track')
        self.assertTrue(row['tracked'])
        self.assertFalse(learner_row(self.cd, self.f.old_enr)['tracked'])

    def test_timeline(self):
        f = self.f
        tl = learner_timeline(self.cd, f.ada.id)
        m1 = tl['modules'][0]
        self.assertEqual((m1['active_s'], m1['visits'], m1['pct']), (350, 2, 0))
        text = m1['activities'][0]['resources'][0]
        self.assertEqual((text['active_s'], text['visits'], text['scroll_pct']), (150, 2, 80))
        self.assertIsNotNone(text['completed_at'])
        video = m1['activities'][0]['resources'][1]
        self.assertEqual(video['video_pct'], 40)
        self.assertIsNone(learner_timeline(self.cd, f.creator.id))

    def test_timeline_quiz_answers_with_timing(self):
        quiz = learner_timeline(self.cd, self.f.ev.id)['modules'][0]['activities'][1]['resources'][0]
        first, second = quiz['quiz_answers']
        self.assertEqual((first['selected_text'], first['is_correct'], first['seconds']), ('b', False, 30))
        self.assertEqual((second['selected_text'], second['is_correct'], second['seconds']), ('c', False, None))

    def test_not_tracked_learner(self):
        text = learner_timeline(self.cd, self.f.old.id)['modules'][0]['activities'][0]['resources'][0]
        self.assertEqual(text['visits'], 0)
        self.assertIsNotNone(text['completed_at'])

    def test_quiz_answers_survive_edited_quiz(self):
        f = self.f
        f.quiz.quiz_data = f.quiz.quiz_data[:1]
        f.quiz.quiz_data[0]['options'] = f.quiz.quiz_data[0]['options'][:1]
        f.quiz.save()
        cd = CourseData(f.course, now=NOW)
        answers = cd.quiz_answers(f.ev.id, cd.resource_by_id[f.quiz.id])
        self.assertEqual(len(answers), 1)
        self.assertIsNone(answers[0]['selected_text'])   # picked option 1 no longer exists
        self.assertFalse(answers[0]['is_correct'])       # stored result still wins
        content_tree(cd)                                 # and nothing else breaks
