from io import BytesIO

from django.contrib.auth.models import User
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, Lesson, Module, UserProfile


def make_course(creator, title='Exportable Course'):
    pillar = LearningPillar.objects.get_or_create(
        slug='teach-with-ai', defaults={'name': 'Teach with AI', 'description': 'd', 'order': 1},
    )[0]
    course = Course.objects.create(
        title=title, description='Desc', pillar=pillar, level='intermediate',
        duration_hours=4, content_format='mixed',
        learning_outcomes=['Outcome one', 'Outcome two'],
        is_published=False, created_by=creator,
    )
    m1 = Module.objects.create(course=course, title='M1', description='first', order=1, duration_minutes=30)
    m2 = Module.objects.create(course=course, title='M2', order=2)
    Lesson.objects.create(module=m1, title='Intro text', lesson_type='text',
                          content='Hello', order=1, is_required=True, duration_minutes=10)
    Lesson.objects.create(module=m1, title='Watch this', lesson_type='video',
                          content='https://youtu.be/dQw4w9WgXcQ', order=2, is_required=False)
    Lesson.objects.create(
        module=m2, title='Check', lesson_type='quiz', order=1, is_required=True,
        quiz_data=[{
            'question': 'Pick two',
            'options': [
                {'text': 'A1', 'is_correct': True},
                {'text': 'B1', 'is_correct': False},
                {'text': 'C1', 'is_correct': True},
            ],
        }],
    )
    return course


class ExportXlsxTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='xlsx_cc', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = User.objects.create_user(username='xlsx_t', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)
        self.course = make_course(self.creator)
        self.url = reverse('authoring-course-export', kwargs={'pk': self.course.pk})

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_export_workbook_structure(self):
        self.client.force_authenticate(self.creator)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', res['Content-Type'])
        self.assertIn('exportable-course.xlsx', res['Content-Disposition'])

        wb = load_workbook(BytesIO(res.getvalue()))
        self.assertEqual(
            set(wb.sheetnames),
            {'README', 'Course', 'Modules', 'Lessons', 'Quiz', 'Choices'},
        )
        self.assertEqual(wb['Choices'].sheet_state, 'hidden')

        course_ws = wb['Course']
        self.assertEqual(course_ws['A2'].value, 'Exportable Course')
        self.assertEqual(course_ws['C2'].value, 'teach-with-ai')
        self.assertEqual(course_ws['D2'].value, 'intermediate')
        self.assertEqual(course_ws['G2'].value, 'Outcome one\nOutcome two')

        lessons_ws = wb['Lessons']
        rows = list(lessons_ws.iter_rows(min_row=2, values_only=True))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][4], 'video')   # lesson_type column
        self.assertEqual(rows[1][7], 'no')      # required column

        quiz_ws = wb['Quiz']
        qrow = list(quiz_ws.iter_rows(min_row=2, values_only=True))[0]
        self.assertEqual(qrow[0], 2)            # module_order (separate column)
        self.assertEqual(qrow[1], 1)            # lesson_order (separate column)
        self.assertEqual(qrow[3], 'Pick two')
        self.assertEqual(qrow[10], 'A,C')       # correct letters

    def test_export_has_dropdown_validations(self):
        self.client.force_authenticate(self.creator)
        res = self.client.get(self.url)
        wb = load_workbook(BytesIO(res.getvalue()))
        self.assertGreaterEqual(len(wb['Lessons'].data_validations.dataValidation), 2)
        self.assertGreaterEqual(len(wb['Course'].data_validations.dataValidation), 3)
