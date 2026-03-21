from django.urls import reverse
from rest_framework import status

from hub.models import Course, CourseEditHistory, Lesson, Module
from hub.tests.test_authoring_courses import AuthoringTestCase

# ── Module creation ───────────────────────────────────────────────────────────

class AuthoringModuleCreateTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-module-create', kwargs={'pk': self.course.pk})

    def test_creates_module(self):
        response = self.client.post(self.url, {'title': 'New Module', 'duration_minutes': 60})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Module.objects.filter(title='New Module', course=self.course).exists())

    def test_auto_assigns_next_order(self):
        # Existing modules have order 1 and 2; new module should get order 3
        response = self.client.post(self.url, {'title': 'Third Module', 'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        module = Module.objects.get(pk=response.data['id'])
        self.assertEqual(module.order, 3)

    def test_first_module_gets_order_one(self):
        empty_course = Course.objects.create(title='Empty', pillar=self.pillar1)
        url = reverse('authoring-module-create', kwargs={'pk': empty_course.pk})
        response = self.client.post(url, {'title': 'First', 'duration_minutes': 20})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['order'], 1)

    def test_create_module_creates_history(self):
        self.client.post(self.url, {'title': 'New Module', 'duration_minutes': 60})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_added', history.changes)
        self.assertEqual(history.changes['module_added']['title'], 'New Module')

    def test_create_module_nonexistent_course_returns_404(self):
        response = self.client.post(
            reverse('authoring-module-create', kwargs={'pk': 9999}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_module_missing_title_returns_400(self):
        response = self.client.post(self.url, {'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ── Module edit / delete ──────────────────────────────────────────────────────

class AuthoringModuleDetailTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse(
            'authoring-module-detail',
            kwargs={'pk': self.course.pk, 'module_pk': self.module1.pk},
        )

    def test_patch_updates_title(self):
        response = self.client.patch(self.url, {'title': 'Updated Module'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.title, 'Updated Module')

    def test_patch_updates_description(self):
        response = self.client.patch(self.url, {'description': 'New desc.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.description, 'New desc.')

    def test_patch_updates_duration_minutes(self):
        response = self.client.patch(self.url, {'duration_minutes': 90})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.duration_minutes, 90)

    def test_patch_creates_history(self):
        self.client.patch(self.url, {'title': 'Renamed Module'})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_edited', history.changes)
        self.assertIn('title', history.changes['module_edited']['fields'])

    def test_patch_history_records_old_and_new(self):
        self.client.patch(self.url, {'duration_minutes': 90})
        history = CourseEditHistory.objects.get(course=self.course)
        field_change = history.changes['module_edited']['fields']['duration_minutes']
        self.assertEqual(field_change['old'], 30)
        self.assertEqual(field_change['new'], 90)

    def test_patch_with_no_changes_creates_no_history(self):
        self.client.patch(self.url, {'title': 'Module 1', 'duration_minutes': 30})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 0)

    def test_patch_nonexistent_module_returns_404(self):
        response = self.client.patch(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_module_belonging_to_other_course_returns_404(self):
        other_course = Course.objects.create(title='Other', pillar=self.pillar1)
        other_module = Module.objects.create(title='Other mod', course=other_course, order=1)
        response = self.client.patch(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': other_module.pk}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_module(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Module.objects.filter(pk=self.module1.pk).exists())

    def test_delete_creates_history(self):
        self.client.delete(self.url)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_deleted', history.changes)
        self.assertEqual(history.changes['module_deleted']['title'], 'Module 1')

    def test_delete_nonexistent_module_returns_404(self):
        response = self.client.delete(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ── Module editor (GET with lessons) ──────────────────────────────────────────

class AuthoringModuleEditorTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.lesson1 = Lesson.objects.create(
            module=self.module1, title='Intro Video', lesson_type='video',
            description='Watch this.', order=1, is_required=True,
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module1, title='Key Concepts', lesson_type='text',
            content='Some markdown.', order=2, is_required=False,
        )
        self.url = reverse('authoring-module-editor', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })

    def test_get_returns_module_with_lessons(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Module 1')
        self.assertEqual(len(response.data['lessons']), 2)

    def test_lessons_include_expected_fields(self):
        response = self.client.get(self.url)
        lesson = response.data['lessons'][0]
        for field in ('id', 'title', 'description', 'lesson_type', 'content', 'duration_minutes', 'order', 'is_required'):
            self.assertIn(field, lesson)

    def test_lessons_ordered_by_order(self):
        response = self.client.get(self.url)
        orders = [lesson['order'] for lesson in response.data['lessons']]
        self.assertEqual(orders, sorted(orders))

    def test_get_nonexistent_module_returns_404(self):
        response = self.client.get(
            reverse('authoring-module-editor', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_access_module_editor(self):
        self._login_as(self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Lesson creation ───────────────────────────────────────────────────────────

class AuthoringLessonCreateTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-lesson-create', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })
        self.valid_payload = {'title': 'New Lesson', 'lesson_type': 'text'}

    def test_create_lesson_returns_201(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_persists_to_db(self):
        self.client.post(self.url, self.valid_payload)
        self.assertTrue(Lesson.objects.filter(title='New Lesson', module=self.module1).exists())

    def test_create_lesson_auto_assigns_order(self):
        Lesson.objects.create(module=self.module1, title='First', lesson_type='text', order=1)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(lesson.order, 2)

    def test_first_lesson_gets_order_one(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.data['order'], 1)

    def test_create_lesson_records_history(self):
        self.client.post(self.url, self.valid_payload)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_added', history.changes)
        self.assertEqual(history.changes['lesson_added']['lesson_title'], 'New Lesson')

    def test_create_lesson_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lesson_nonexistent_module_returns_404(self):
        url = reverse('authoring-lesson-create', kwargs={'pk': self.course.pk, 'module_pk': 9999})
        response = self.client.post(url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_lesson_missing_title_returns_400(self):
        response = self.client.post(self.url, {'lesson_type': 'text'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lesson_invalid_type_returns_400(self):
        response = self.client.post(self.url, {'title': 'X', 'lesson_type': 'podcast'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_create_lesson(self):
        self._login_as(self.teacher)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_lesson_with_all_fields(self):
        payload = {
            'title': 'Full Lesson',
            'lesson_type': 'video',
            'description': 'A video lesson.',
            'content': '',
            'duration_minutes': 15,
            'is_required': False,
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(lesson.duration_minutes, 15)
        self.assertFalse(lesson.is_required)


# ── Lesson edit / delete ──────────────────────────────────────────────────────

class AuthoringLessonDetailTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.lesson = Lesson.objects.create(
            module=self.module1, title='Intro Text', lesson_type='text',
            description='Original desc.', content='Original content.',
            duration_minutes=10, order=1, is_required=True,
        )
        self.url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': self.lesson.pk,
        })

    def test_patch_updates_title(self):
        response = self.client.patch(self.url, {'title': 'Updated Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Title')

    def test_patch_updates_content(self):
        response = self.client.patch(self.url, {'content': '# New Markdown'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.content, '# New Markdown')

    def test_patch_updates_lesson_type(self):
        response = self.client.patch(self.url, {'lesson_type': 'quiz'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.lesson_type, 'quiz')

    def test_patch_updates_duration(self):
        response = self.client.patch(self.url, {'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.duration_minutes, 30)

    def test_patch_updates_is_required(self):
        response = self.client.patch(self.url, {'is_required': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertFalse(self.lesson.is_required)

    def test_patch_creates_history(self):
        self.client.patch(self.url, {'title': 'Renamed Lesson'})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_edited', history.changes)
        self.assertIn('title', history.changes['lesson_edited']['fields'])

    def test_patch_history_records_old_and_new(self):
        self.client.patch(self.url, {'duration_minutes': 45})
        history = CourseEditHistory.objects.get(course=self.course)
        field_change = history.changes['lesson_edited']['fields']['duration_minutes']
        self.assertEqual(field_change['old'], 10)
        self.assertEqual(field_change['new'], 45)

    def test_patch_with_no_changes_creates_no_history(self):
        self.client.patch(self.url, {'title': 'Intro Text', 'duration_minutes': 10})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 0)

    def test_patch_nonexistent_lesson_returns_404(self):
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': 9999,
        })
        response = self.client.patch(url, {'title': 'X'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_lesson_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.patch(self.url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_lesson_belonging_to_other_module_returns_404(self):
        other_lesson = Lesson.objects.create(
            module=self.module2, title='Other', lesson_type='text', order=1,
        )
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': other_lesson.pk,
        })
        response = self.client.patch(url, {'title': 'X'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_lesson(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_delete_creates_history(self):
        self.client.delete(self.url)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_deleted', history.changes)
        self.assertEqual(history.changes['lesson_deleted']['lesson_title'], 'Intro Text')

    def test_delete_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_nonexistent_lesson_returns_404(self):
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': 9999,
        })
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_patch_lesson(self):
        self._login_as(self.teacher)
        response = self.client.patch(self.url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_delete_lesson(self):
        self._login_as(self.teacher)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Quiz data ─────────────────────────────────────────────────────────────────

VALID_QUIZ = [
    {
        'question': 'What is machine learning?',
        'options': [
            {'text': 'A type of robot',        'is_correct': False},
            {'text': 'Learning from data',      'is_correct': True},
            {'text': 'A programming language',  'is_correct': False},
            {'text': 'A database system',       'is_correct': False},
        ],
    },
    {
        'question': 'Which of these are AI applications? (select all that apply)',
        'options': [
            {'text': 'Image recognition', 'is_correct': True},
            {'text': 'Spell check',        'is_correct': True},
            {'text': 'A hammer',           'is_correct': False},
        ],
    },
]


class QuizDataTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.create_url = reverse('authoring-lesson-create', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })
        self.quiz_lesson = Lesson.objects.create(
            module=self.module1, title='Knowledge Check', lesson_type='quiz',
            order=1, quiz_data=VALID_QUIZ,
        )
        self.detail_url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
            'lesson_pk': self.quiz_lesson.pk,
        })

    # ── Creation ──

    def test_create_quiz_lesson_with_valid_quiz_data(self):
        payload = {'title': 'Quiz 1', 'lesson_type': 'quiz', 'quiz_data': VALID_QUIZ}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(len(lesson.quiz_data), 2)

    def test_create_quiz_lesson_quiz_data_returned_in_response(self):
        payload = {'title': 'Quiz 1', 'lesson_type': 'quiz', 'quiz_data': VALID_QUIZ}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['quiz_data']), 2)
        self.assertEqual(response.data['quiz_data'][0]['question'], 'What is machine learning?')

    def test_create_quiz_with_multiple_correct_options(self):
        payload = {'title': 'Multi-answer Quiz', 'lesson_type': 'quiz', 'quiz_data': VALID_QUIZ}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        q2_options = response.data['quiz_data'][1]['options']
        correct = [o for o in q2_options if o['is_correct']]
        self.assertEqual(len(correct), 2)

    def test_create_quiz_defaults_quiz_data_to_empty_list(self):
        response = self.client.post(self.create_url, {'title': 'Empty Quiz', 'lesson_type': 'quiz'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quiz_data'], [])

    # ── Validation ──

    def test_quiz_data_not_a_list_returns_400(self):
        payload = {'title': 'Bad', 'lesson_type': 'quiz', 'quiz_data': 'not a list'}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quiz_data_question_not_dict_returns_400(self):
        payload = {'title': 'Bad', 'lesson_type': 'quiz', 'quiz_data': ['not a dict']}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quiz_data_fewer_than_two_options_returns_400(self):
        bad_quiz = [{'question': 'Q?', 'options': [{'text': 'Only one', 'is_correct': True}]}]
        payload = {'title': 'Bad', 'lesson_type': 'quiz', 'quiz_data': bad_quiz}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quiz_data_is_correct_not_bool_returns_400(self):
        bad_quiz = [{
            'question': 'Q?',
            'options': [
                {'text': 'A', 'is_correct': 'yes'},
                {'text': 'B', 'is_correct': False},
            ],
        }]
        payload = {'title': 'Bad', 'lesson_type': 'quiz', 'quiz_data': bad_quiz}
        response = self.client.post(self.create_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Editing ──

    def test_patch_quiz_data_updates_questions(self):
        new_quiz = [{
            'question': 'Updated question?',
            'options': [
                {'text': 'Yes', 'is_correct': True},
                {'text': 'No',  'is_correct': False},
            ],
        }]
        response = self.client.patch(self.detail_url, {'quiz_data': new_quiz}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz_lesson.refresh_from_db()
        self.assertEqual(len(self.quiz_lesson.quiz_data), 1)
        self.assertEqual(self.quiz_lesson.quiz_data[0]['question'], 'Updated question?')

    def test_patch_quiz_data_records_history(self):
        new_quiz = [{
            'question': 'New Q?',
            'options': [
                {'text': 'A', 'is_correct': True},
                {'text': 'B', 'is_correct': False},
            ],
        }]
        self.client.patch(self.detail_url, {'quiz_data': new_quiz}, format='json')
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('quiz_data', history.changes['lesson_edited']['fields'])

    def test_module_editor_returns_quiz_data(self):
        url = reverse('authoring-module-editor', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quiz_lesson_data = next(
            (lesson for lesson in response.data['lessons'] if lesson['id'] == self.quiz_lesson.pk), None,
        )
        self.assertIsNotNone(quiz_lesson_data)
        self.assertIn('quiz_data', quiz_lesson_data)
        self.assertEqual(len(quiz_lesson_data['quiz_data']), 2)


# ── Module reorder ────────────────────────────────────────────────────────────

class AuthoringModuleReorderTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.module3 = Module.objects.create(
            title='Module 3', course=self.course, order=3, duration_minutes=20,
        )
        self.url = reverse('authoring-module-reorder', kwargs={'pk': self.course.pk})

    def test_reorder_changes_module_orders(self):
        new_order = [self.module3.pk, self.module1.pk, self.module2.pk]
        response = self.client.patch(self.url, {'order': new_order}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.module2.refresh_from_db()
        self.module3.refresh_from_db()
        self.assertEqual(self.module3.order, 1)
        self.assertEqual(self.module1.order, 2)
        self.assertEqual(self.module2.order, 3)

    def test_reorder_returns_updated_module_list(self):
        new_order = [self.module2.pk, self.module3.pk, self.module1.pk]
        response = self.client.patch(self.url, {'order': new_order}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [m['id'] for m in response.data]
        self.assertEqual(returned_ids, sorted(returned_ids, key=lambda mid: next(
            i for i, pk in enumerate(new_order) if pk == mid
        )))

    def test_reorder_records_history(self):
        new_order = [self.module2.pk, self.module1.pk, self.module3.pk]
        self.client.patch(self.url, {'order': new_order}, format='json')
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('modules_reordered', history.changes)
        self.assertEqual(history.changes['modules_reordered']['order'], new_order)

    def test_reorder_missing_order_returns_400(self):
        response = self.client.patch(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_empty_order_returns_400(self):
        response = self.client.patch(self.url, {'order': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_invalid_ids_returns_400(self):
        response = self.client.patch(self.url, {'order': [9999, self.module1.pk]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_module_from_other_course_returns_400(self):
        other_course = Course.objects.create(title='Other', pillar=self.pillar1)
        other_module = Module.objects.create(title='Other mod', course=other_course, order=1)
        response = self.client.patch(
            self.url, {'order': [self.module1.pk, other_module.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.patch(
            self.url, {'order': [self.module1.pk, self.module2.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_nonexistent_course_returns_404(self):
        response = self.client.patch(
            reverse('authoring-module-reorder', kwargs={'pk': 9999}),
            {'order': [self.module1.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_reorder_modules(self):
        self._login_as(self.teacher)
        response = self.client.patch(
            self.url, {'order': [self.module1.pk, self.module2.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Lesson reorder ────────────────────────────────────────────────────────────

class AuthoringLessonReorderTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.lesson1 = Lesson.objects.create(
            module=self.module1, title='Lesson 1', lesson_type='text', order=1,
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module1, title='Lesson 2', lesson_type='video', order=2,
        )
        self.lesson3 = Lesson.objects.create(
            module=self.module1, title='Lesson 3', lesson_type='quiz', order=3,
        )
        self.url = reverse('authoring-lesson-reorder', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })

    def test_reorder_changes_lesson_orders(self):
        new_order = [self.lesson3.pk, self.lesson1.pk, self.lesson2.pk]
        response = self.client.patch(self.url, {'order': new_order}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson1.refresh_from_db()
        self.lesson2.refresh_from_db()
        self.lesson3.refresh_from_db()
        self.assertEqual(self.lesson3.order, 1)
        self.assertEqual(self.lesson1.order, 2)
        self.assertEqual(self.lesson2.order, 3)

    def test_reorder_returns_updated_lesson_list(self):
        new_order = [self.lesson2.pk, self.lesson3.pk, self.lesson1.pk]
        response = self.client.patch(self.url, {'order': new_order}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_reorder_records_history(self):
        new_order = [self.lesson2.pk, self.lesson1.pk, self.lesson3.pk]
        self.client.patch(self.url, {'order': new_order}, format='json')
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lessons_reordered', history.changes)
        self.assertEqual(history.changes['lessons_reordered']['order'], new_order)

    def test_reorder_missing_order_returns_400(self):
        response = self.client.patch(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_empty_list_returns_400(self):
        response = self.client.patch(self.url, {'order': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_invalid_ids_returns_400(self):
        response = self.client.patch(self.url, {'order': [9999, self.lesson1.pk]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_lesson_from_other_module_returns_400(self):
        other_lesson = Lesson.objects.create(
            module=self.module2, title='Other', lesson_type='text', order=1,
        )
        response = self.client.patch(
            self.url, {'order': [self.lesson1.pk, other_lesson.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.patch(
            self.url, {'order': [self.lesson1.pk, self.lesson2.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_nonexistent_module_returns_404(self):
        url = f'/api/authoring/courses/{self.course.pk}/modules/9999/lessons/reorder/'
        response = self.client.patch(url, {'order': [self.lesson1.pk]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_reorder_lessons(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(
            self.url, {'order': [self.lesson1.pk, self.lesson2.pk]}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
