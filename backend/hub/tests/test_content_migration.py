from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from hub.content_migration_logic import (
    build_resources_for_lesson,
    migrate_progress_row,
    repoint_submission,
)
from hub.models import (
    Activity,
    AssignmentSubmission,
    Course,
    LearningPillar,
    LessonProgress,
    Module,
    Resource,
    ResourceProgress,
)


class ContentMappingTest(TestCase):
    """Exercises the shared mapping logic (build_resources_for_lesson) that the
    0054 data migration runs — using current models."""

    def setUp(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=self.course, order=1)

        self.text = Activity.objects.create(
            module=self.module, title='Read', lesson_type='text', order=1,
            content='body text',
            media_items=[
                {'type': 'image', 'url': 'i.png', 'caption': 'fig'},
                {'type': 'video', 'url': 'v.mp4', 'caption': ''},
            ],
            translations={'el': {'content': 'κείμενο'}},
        )
        self.video = Activity.objects.create(
            module=self.module, title='Watch', lesson_type='video', order=2,
            content='', media_items=[{'type': 'video', 'url': 'w.mp4', 'caption': 'c'}],
        )
        self.quiz = Activity.objects.create(
            module=self.module, title='Quiz', lesson_type='quiz', order=3,
            content='intro', quiz_data=[{'question': 'Q', 'options': [{'text': 'a', 'is_correct': True}]}],
        )
        self.assign = Activity.objects.create(
            module=self.module, title='Task', lesson_type='assignment', order=4,
            content='do this', is_required=True,
        )

    def _run(self):
        for a in Activity.objects.all():
            build_resources_for_lesson(a, Resource)

    def test_text_lesson_becomes_text_plus_media(self):
        self._run()
        res = list(self.text.resources.order_by('order'))
        self.assertEqual([r.type for r in res], ['text', 'image', 'video'])
        self.assertEqual(res[0].content, 'body text')
        self.assertEqual(res[0].translations, {'el': {'content': 'κείμενο'}})
        self.assertEqual(res[1].url, 'i.png')
        self.assertEqual(res[1].caption, 'fig')

    def test_video_lesson_from_media(self):
        self._run()
        res = list(self.video.resources.all())
        self.assertEqual([r.type for r in res], ['video'])
        self.assertEqual(res[0].url, 'w.mp4')

    def test_quiz_lesson(self):
        self._run()
        res = list(self.quiz.resources.order_by('order'))
        self.assertEqual([r.type for r in res], ['text', 'quiz'])
        self.assertEqual(res[1].quiz_data[0]['question'], 'Q')

    def test_assignment_lesson(self):
        self._run()
        res = list(self.assign.resources.all())
        self.assertEqual([r.type for r in res], ['assignment'])
        self.assertEqual(res[0].instructions, 'do this')

    def test_text_blocks_inside_media_are_kept_in_order(self):
        mixed = Activity.objects.create(
            module=self.module, title='Mixed', lesson_type='image', order=7, content='',
            media_items=[
                {'type': 'text', 'html': '<p>Intro</p>'},
                {'type': 'image', 'url': 'a.png', 'caption': ''},
                {'type': 'text', 'html': '   '},          # empty block: dropped
                {'type': 'text', 'html': '<p>Outro</p>'},
            ],
        )
        build_resources_for_lesson(mixed, Resource)
        res = list(mixed.resources.order_by('order'))
        self.assertEqual([r.type for r in res], ['text', 'image', 'text'])
        self.assertEqual(res[0].content, '<p>Intro</p>')
        self.assertEqual(res[2].content, '<p>Outro</p>')

    def test_malformed_media_items_are_skipped(self):
        bad_list = Activity.objects.create(
            module=self.module, title='BadList', lesson_type='text', order=5,
            content='c', media_items='not-a-list',
        )
        bad_items = Activity.objects.create(
            module=self.module, title='BadItems', lesson_type='text', order=6,
            content='c', media_items=['x', {'type': 'video'}, {'type': 'video', 'url': 'ok.mp4'}],
        )
        self._run()
        self.assertEqual([r.type for r in bad_list.resources.all()], ['text'])
        self.assertEqual([r.type for r in bad_items.resources.order_by('order')], ['text', 'video'])


class ProgressMappingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=self.course, order=1)
        self.textlesson = Activity.objects.create(
            module=self.module, title='Read', lesson_type='text', order=1, content='b',
        )
        self.quizlesson = Activity.objects.create(
            module=self.module, title='Quiz', lesson_type='quiz', order=2,
            content='', quiz_data=[{'question': 'Q', 'options': []}],
        )
        self.assignlesson = Activity.objects.create(
            module=self.module, title='Task', lesson_type='assignment', order=3, content='x',
        )
        LessonProgress.objects.create(
            user=self.user, lesson=self.textlesson, completed_at=timezone.now(),
            time_spent_seconds=120,
        )
        LessonProgress.objects.create(
            user=self.user, lesson=self.quizlesson, completed_at=timezone.now(), quiz_score=0.8,
        )
        self.submission = AssignmentSubmission.objects.create(
            user=self.user, lesson=self.assignlesson, text='answer',
        )

    def test_progress_and_submissions_migrate(self):
        for a in Activity.objects.all():
            build_resources_for_lesson(a, Resource)
        for lp in LessonProgress.objects.all():
            migrate_progress_row(lp, Resource, ResourceProgress)
        for sub in AssignmentSubmission.objects.filter(resource__isnull=True):
            repoint_submission(sub, Resource)

        text_res = self.textlesson.resources.get()
        rp = ResourceProgress.objects.get(user=self.user, resource=text_res)
        self.assertIsNotNone(rp.completed_at)
        self.assertEqual(rp.time_spent_seconds, 120)

        quiz_res = self.quizlesson.resources.get(type='quiz')
        rp_quiz = ResourceProgress.objects.get(user=self.user, resource=quiz_res)
        self.assertEqual(rp_quiz.quiz_score, 0.8)

        assign_res = self.assignlesson.resources.get(type='assignment')
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.resource_id, assign_res.id)


class ProgressParityTest(TestCase):
    """The plan's parity gate: after migrating, recomputing progress from
    resources must give each enrollment the same % the legacy lesson-count
    calculation did — including partial progress across multi-resource
    lessons and legacy rows whose completed_at is NULL."""

    def setUp(self):
        from hub.models import Enrollment
        self.user = User.objects.create_user(username='parity', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        module = Module.objects.create(title='M', course=self.course, order=1)
        # A: text + 2 media → 3 resources. B: plain text → 1 resource.
        self.a = Activity.objects.create(
            module=module, title='A', lesson_type='text', order=1, content='x',
            media_items=[{'type': 'image', 'url': 'i', 'caption': ''},
                         {'type': 'video', 'url': 'v', 'caption': ''}],
        )
        self.b = Activity.objects.create(
            module=module, title='B', lesson_type='text', order=2, content='y',
        )
        self.optional = Activity.objects.create(
            module=module, title='Opt', lesson_type='text', order=3, content='z',
            is_required=False,
        )
        # Legacy: only A done, recorded like the seed does (completed_at NULL).
        LessonProgress.objects.create(user=self.user, lesson=self.a)
        self.enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, progress_pct=50,  # legacy: 1 of 2 required
        )

    def test_partial_progress_is_preserved(self):
        from hub.completion import completed_activity_ids, recompute_course_progress
        for act in Activity.objects.all():
            build_resources_for_lesson(act, Resource)
        for lp in LessonProgress.objects.all():
            migrate_progress_row(lp, Resource, ResourceProgress)

        self.assertEqual(recompute_course_progress(self.user, self.enrollment), 50)
        self.assertEqual(completed_activity_ids(self.user, self.course), {self.a.id})
