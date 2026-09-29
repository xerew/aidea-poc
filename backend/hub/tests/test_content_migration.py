import importlib

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import (
    AssignmentSubmission,
    Course,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    ResourceProgress,
)

# The migration modules aren't importable by dotted name (leading digits), so
# load the forward functions via importlib.
_content_mig = importlib.import_module('hub.migrations.0054_split_lessons_into_resources')
_progress_mig = importlib.import_module('hub.migrations.0055_migrate_progress_and_submissions')


class ContentMigrationTest(TestCase):
    def setUp(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=self.course, order=1)

        self.text = Lesson.objects.create(
            module=self.module, title='Read', lesson_type='text', order=1,
            content='body text',
            media_items=[
                {'type': 'image', 'url': 'i.png', 'caption': 'fig'},
                {'type': 'video', 'url': 'v.mp4', 'caption': ''},
            ],
            translations={'el': {'content': 'κείμενο'}},
        )
        self.video = Lesson.objects.create(
            module=self.module, title='Watch', lesson_type='video', order=2,
            content='', media_items=[{'type': 'video', 'url': 'w.mp4', 'caption': 'c'}],
        )
        self.quiz = Lesson.objects.create(
            module=self.module, title='Quiz', lesson_type='quiz', order=3,
            content='intro', quiz_data=[{'question': 'Q', 'options': [{'text': 'a', 'is_correct': True}]}],
        )
        self.assign = Lesson.objects.create(
            module=self.module, title='Task', lesson_type='assignment', order=4,
            content='do this', is_required=True,
        )

    def _run_content(self):
        _content_mig.migrate_lessons_to_resources(django_apps, None)

    def test_text_lesson_becomes_text_plus_media(self):
        self._run_content()
        res = list(self.text.resources.order_by('order'))
        self.assertEqual([r.type for r in res], ['text', 'image', 'video'])
        self.assertEqual(res[0].content, 'body text')
        self.assertEqual(res[0].translations, {'el': {'content': 'κείμενο'}})
        self.assertEqual(res[1].url, 'i.png')
        self.assertEqual(res[1].caption, 'fig')

    def test_video_lesson_from_media(self):
        self._run_content()
        res = list(self.video.resources.all())
        self.assertEqual([r.type for r in res], ['video'])
        self.assertEqual(res[0].url, 'w.mp4')

    def test_quiz_lesson(self):
        self._run_content()
        res = list(self.quiz.resources.order_by('order'))
        self.assertEqual([r.type for r in res], ['text', 'quiz'])
        self.assertEqual(res[1].quiz_data[0]['question'], 'Q')

    def test_assignment_lesson(self):
        self._run_content()
        res = list(self.assign.resources.all())
        self.assertEqual([r.type for r in res], ['assignment'])
        self.assertEqual(res[0].instructions, 'do this')


class ProgressMigrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=self.course, order=1)
        self.textlesson = Lesson.objects.create(
            module=self.module, title='Read', lesson_type='text', order=1, content='b',
        )
        self.quizlesson = Lesson.objects.create(
            module=self.module, title='Quiz', lesson_type='quiz', order=2,
            content='', quiz_data=[{'question': 'Q', 'options': []}],
        )
        self.assignlesson = Lesson.objects.create(
            module=self.module, title='Task', lesson_type='assignment', order=3, content='x',
        )
        from django.utils import timezone
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
        _content_mig.migrate_lessons_to_resources(django_apps, None)
        _progress_mig.migrate_progress_and_submissions(django_apps, None)

        # text lesson's single resource is completed for the learner
        text_res = self.textlesson.resources.get()
        rp = ResourceProgress.objects.get(user=self.user, resource=text_res)
        self.assertIsNotNone(rp.completed_at)
        self.assertEqual(rp.time_spent_seconds, 120)

        # quiz score lands on the quiz resource
        quiz_res = self.quizlesson.resources.get(type='quiz')
        rp_quiz = ResourceProgress.objects.get(user=self.user, resource=quiz_res)
        self.assertEqual(rp_quiz.quiz_score, 0.8)

        # submission repointed to the assignment resource
        assign_res = self.assignlesson.resources.get(type='assignment')
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.resource_id, assign_res.id)
