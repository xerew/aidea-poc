from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from hub.content_migration_logic import build_resources_for_lesson
from hub.models import Activity, Course, LearningPillar, Module, Resource, UserProfile
from hub.xlsx_transfer import build_course_workbook

SHEETS = {'README', 'Choices', 'Course', 'Modules', 'Activities', 'Resources', 'Quiz', 'Translations'}
QUIZ = [{
    'question': 'Pick two',
    'options': [
        {'text': 'A1', 'is_correct': True},
        {'text': 'B1', 'is_correct': False},
        {'text': 'C1', 'is_correct': True},
    ],
}]


def _pillar(slug='teach-with-ai', order=1):
    return LearningPillar.objects.get_or_create(
        slug=slug, defaults={'name': slug.replace('-', ' ').title(), 'description': 'd', 'order': order},
    )[0]


def make_course(creator, title='Exportable Course'):
    """Two modules; activities built from lesson fields the way migrated data looks."""
    course = Course.objects.create(
        title=title, description='Desc', pillar=_pillar(), level='intermediate',
        duration_hours=4, content_format='mixed',
        learning_outcomes=['Outcome one', 'Outcome two'],
        is_published=False, created_by=creator,
    )
    m1 = Module.objects.create(course=course, title='M1', description='first', order=1,
                               duration_minutes=30, related_outcomes=[1])
    m2 = Module.objects.create(course=course, title='M2', order=2)
    for activity in (
        Activity.objects.create(module=m1, title='Intro text', lesson_type='text',
                                content='Hello', order=1, is_required=True, duration_minutes=10),
        Activity.objects.create(module=m1, title='Watch this', lesson_type='video', order=2,
                                is_required=False,
                                media_items=[{'type': 'video', 'url': 'https://youtu.be/x', 'caption': 'Clip'}]),
        Activity.objects.create(module=m2, title='Check', lesson_type='quiz', order=1,
                                is_required=True, quiz_data=QUIZ),
    ):
        build_resources_for_lesson(activity, Resource)
    return course


def _bytes(wb):
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


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
        self.assertEqual(set(wb.sheetnames), SHEETS)
        self.assertEqual(wb['Choices'].sheet_state, 'hidden')

        course_ws = wb['Course']
        self.assertEqual(course_ws['A2'].value, 'Exportable Course')
        self.assertEqual(course_ws['C2'].value, 'teach-with-ai')
        self.assertEqual(course_ws['D2'].value, 'intermediate')
        self.assertEqual(course_ws['G2'].value, 'Outcome one\nOutcome two')
        self.assertEqual(wb['Modules']['E2'].value, '2')  # related outcome numbers, 1-based

        activities = list(wb['Activities'].iter_rows(min_row=2, values_only=True))
        self.assertEqual([a[2] for a in activities], ['Intro text', 'Watch this', 'Check'])

        resources = list(wb['Resources'].iter_rows(min_row=2, values_only=True))
        video = next(r for r in resources if r[3] == 'video')
        self.assertEqual((video[0], video[1], video[2]), (1, 2, 1))  # module, activity, resource order
        self.assertEqual(video[4], 'no')                              # required
        self.assertEqual((video[7], video[8]), ('https://youtu.be/x', 'Clip'))

        qrow = list(wb['Quiz'].iter_rows(min_row=2, values_only=True))[0]
        self.assertEqual(qrow[:4], (2, 1, 1, 1))
        self.assertEqual(qrow[4], 'Pick two')
        self.assertEqual(qrow[11], 'A,C')

    def test_export_includes_resources_authored_without_lesson_fields(self):
        """Content added through the resource editor never touches the legacy
        lesson columns — it must still be exported."""
        activity = Activity.objects.create(module=self.course.modules.get(order=2), title='New', order=2)
        Resource.objects.create(activity=activity, type='assignment', order=1, instructions='Reflect')
        wb = build_course_workbook(self.course)
        rows = list(wb['Resources'].iter_rows(min_row=2, values_only=True))
        self.assertIn('Reflect', [r[9] for r in rows])

    def test_export_has_dropdown_validations(self):
        self.client.force_authenticate(self.creator)
        wb = load_workbook(BytesIO(self.client.get(self.url).getvalue()))
        self.assertGreaterEqual(len(wb['Resources'].data_validations.dataValidation), 2)
        self.assertGreaterEqual(len(wb['Course'].data_validations.dataValidation), 3)


class TemplateXlsxTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='xlsx_tpl', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = User.objects.create_user(username='xlsx_tpl_t', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)
        _pillar()  # dropdowns need at least one pillar
        self.url = reverse('authoring-course-template')

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_template_is_blank_but_structured(self):
        self.client.force_authenticate(self.creator)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('aidea-course-template.xlsx', res['Content-Disposition'])
        wb = load_workbook(BytesIO(res.getvalue()))
        self.assertEqual(set(wb.sheetnames), SHEETS)
        self.assertEqual(wb['Course']['A1'].value, 'title')
        self.assertEqual(wb['Course']['O1'].value, 'prior_knowledge')
        self.assertIsNone(wb['Course']['A2'].value)
        self.assertEqual(list(wb['Modules'].iter_rows(min_row=2, values_only=True)), [])
        self.assertGreaterEqual(len(wb['Course'].data_validations.dataValidation), 3)


class ImportXlsxTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='xlsx_imp', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = User.objects.create_user(username='xlsx_imp_t', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)
        self.course = make_course(self.creator, title='Round Trip')
        self.url = reverse('authoring-course-import')

    def _post(self, buf, name='course.xlsx'):
        upload = SimpleUploadedFile(
            name, buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        return self.client.post(self.url, {'file': upload}, format='multipart')

    def _import(self, wb):
        self.client.force_authenticate(self.creator)
        res = self._post(_bytes(wb))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, getattr(res, 'data', None))
        return Course.objects.get(pk=res.data['id'])

    def _errors(self, wb):
        self.client.force_authenticate(self.creator)
        res = self._post(_bytes(wb))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.filter(title__startswith='Round Trip (imported').count(), 0)
        return res.data['errors']

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self._post(_bytes(build_course_workbook(self.course))).status_code, 403)

    def test_round_trip(self):
        new = self._import(build_course_workbook(self.course))
        self.assertEqual(new.title, 'Round Trip (imported)')  # collision with original
        self.assertFalse(new.is_published)
        self.assertEqual(new.created_by, self.creator)
        self.assertEqual(new.level, self.course.level)
        self.assertEqual(new.learning_outcomes, self.course.learning_outcomes)
        self.assertEqual(new.modules.get(order=1).related_outcomes, [1])
        quiz = Resource.objects.get(activity__module__course=new, type='quiz')
        self.assertEqual(quiz.quiz_data, QUIZ)
        video = Resource.objects.get(activity__module__course=new, type='video')
        self.assertFalse(video.is_required)
        self.assertEqual((video.url, video.caption), ('https://youtu.be/x', 'Clip'))
        # Every imported activity has resources.
        self.assertFalse(Activity.objects.filter(module__course=new, resources__isnull=True).exists())

    def test_round_trip_preserves_course_profile(self):
        self.course.additional_pillars.add(_pillar('teach-for-ai', 2))
        self.course.cross_axis_relevance = 'Also builds AI literacy.'
        self.course.target_audience = ['teachers', 'school_leaders']
        self.course.target_audience_other = 'Trainers'
        self.course.educational_levels = ['upper_secondary']
        self.course.educational_level_other = 'VET'
        self.course.prior_knowledge = 'None'
        self.course.save()
        new = self._import(build_course_workbook(self.course))
        self.assertEqual(list(new.additional_pillars.values_list('slug', flat=True)), ['teach-for-ai'])
        self.assertEqual(new.cross_axis_relevance, 'Also builds AI literacy.')
        self.assertEqual(new.target_audience, ['teachers', 'school_leaders'])
        self.assertEqual(new.target_audience_other, 'Trainers')
        self.assertEqual(new.educational_levels, ['upper_secondary'])
        self.assertEqual(new.educational_level_other, 'VET')
        self.assertEqual(new.prior_knowledge, 'None')

    def test_round_trip_preserves_translations(self):
        self.course.translations = {'el': {
            'title': 'Τίτλος', 'learning_outcomes': ['Στόχος 1', 'Στόχος 2'], 'prior_knowledge': 'Καμία',
        }}
        self.course.translation_status = {'el': 'reviewed'}
        self.course.save()
        m1 = self.course.modules.get(order=1)
        m1.translations = {'el': {'title': 'Ενότητα'}}
        m1.save()
        intro = m1.lessons.get(order=1)
        intro.translations = {'el': {'title': 'Εισαγωγή'}}
        intro.save()
        text = intro.resources.get()
        text.translations = {'el': {'content': 'Γεια'}}
        text.save()
        quiz = Resource.objects.get(activity__module=self.course.modules.get(order=2), type='quiz')
        quiz_tr = [{'question': 'Διάλεξε', 'options': [
            {'text': 'Α', 'is_correct': True}, {'text': 'Β', 'is_correct': False},
            {'text': 'Γ', 'is_correct': True}]}]
        quiz.translations = {'el': {'quiz_data': quiz_tr}}
        quiz.save()

        new = self._import(build_course_workbook(self.course))
        self.assertEqual(new.translations['el']['title'], 'Τίτλος')
        self.assertEqual(new.translations['el']['learning_outcomes'], ['Στόχος 1', 'Στόχος 2'])
        self.assertEqual(new.translations['el']['prior_knowledge'], 'Καμία')
        self.assertEqual(new.translation_status['el'], 'reviewed')
        new_m1 = new.modules.get(order=1)
        self.assertEqual(new_m1.translations['el']['title'], 'Ενότητα')
        new_intro = new_m1.lessons.get(order=1)
        self.assertEqual(new_intro.translations['el']['title'], 'Εισαγωγή')
        self.assertEqual(new_intro.resources.get().translations['el']['content'], 'Γεια')
        new_quiz = Resource.objects.get(activity__module__course=new, type='quiz')
        self.assertEqual(new_quiz.translations['el']['quiz_data'], quiz_tr)

    def test_round_trip_preserves_subjects(self):
        from hub.models import Subject
        self.course.subjects.set([Subject.objects.get(slug='physics'), Subject.objects.get(slug='astronomy')])
        new = self._import(build_course_workbook(self.course))
        self.assertEqual(set(new.subjects.values_list('slug', flat=True)), {'physics', 'astronomy'})

    def test_unknown_subject_slug_rejected(self):
        wb = build_course_workbook(self.course)
        wb['Course']['H2'] = 'not-a-subject'
        self.assertTrue(any('unknown subject' in e.lower() for e in self._errors(wb)))

    def test_invalid_profile_choices_rejected(self):
        wb = build_course_workbook(self.course)
        wb['Course']['K2'] = 'teachers,parents'
        wb['Course']['M2'] = 'kindergarten'
        errors = self._errors(wb)
        self.assertTrue(any('Course!K2' in e for e in errors))
        self.assertTrue(any('Course!M2' in e for e in errors))

    def test_out_of_range_related_outcome_rejected(self):
        wb = build_course_workbook(self.course)
        wb['Modules']['E2'] = '3'  # only two outcomes
        self.assertTrue(any('Modules!E2' in e for e in self._errors(wb)))

    def test_invalid_resource_type_rejected_with_cell_ref(self):
        wb = build_course_workbook(self.course)
        wb['Resources']['D2'] = 'vido'
        self.assertTrue(any('Resources!D2' in e for e in self._errors(wb)))

    def test_activity_without_resources_rejected(self):
        wb = build_course_workbook(self.course)
        wb['Activities'].append([2, 5, 'Empty', '', 0])
        self.assertTrue(any('has no resources' in e for e in self._errors(wb)))

    def test_media_resource_needs_url(self):
        wb = build_course_workbook(self.course)
        ws = wb['Resources']
        row = next(r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=4).value == 'video')
        ws.cell(row=row, column=8, value='')
        self.assertTrue(any(f'Resources!H{row}' in e for e in self._errors(wb)))

    def test_wrong_extension_rejected(self):
        self.client.force_authenticate(self.creator)
        res = self._post(BytesIO(b'not a workbook'), name='course.csv')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_out_of_range_integers_rejected(self):
        # PositiveSmallIntegerField caps at 32767 on Postgres; must 400, not 500
        wb = build_course_workbook(self.course)
        wb['Course']['E2'] = 99999       # duration_hours over smallint max
        wb['Activities']['E2'] = -5      # negative duration_minutes
        errors = self._errors(wb)
        self.assertTrue(any('Course!E2' in e for e in errors))
        self.assertTrue(any('Activities!E2' in e for e in errors))

    def test_corrupt_xlsx_bytes_rejected_cleanly(self):
        self.client.force_authenticate(self.creator)
        res = self._post(BytesIO(b'\x00\x01garbage not a zip'), name='course.xlsx')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not a valid xlsx workbook', res.data['errors'][0])

