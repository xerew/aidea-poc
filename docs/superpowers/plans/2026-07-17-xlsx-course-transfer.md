# Course xlsx Export/Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Content creators can download any course as a structured xlsx workbook (with in-cell dropdowns for every platform choice-set) and import such a workbook to create a new draft course.

**Architecture:** A single backend module `hub/xlsx_transfer.py` owns the workbook format (builder + parser); two thin DRF views expose it; the Authoring page gets Export/Import controls. Spec: `docs/superpowers/specs/2026-07-17-xlsx-course-transfer-design.md`.

**Tech Stack:** Django/DRF, `openpyxl` (new dependency), React Authoring page.

## Global Constraints

- Backend runner: from `backend/`, `.venv/Scripts/uv.exe run ...` (fallback `C:\Users\Nikos A. Grammatikos\.local\bin\uv.exe run ...`; ignore the VIRTUAL_ENV stderr warning)
- Backend tests: `uv.exe run manage.py test hub.tests.test_xlsx_transfer -v 2`; full suite `uv.exe run manage.py test hub analytics -v 1` must stay green (357+ tests)
- Lint: `uv.exe run ruff check . --fix`; frontend `npm run lint && npm run build` warning-free
- Both endpoints `IsContentCreator`; import: `.xlsx` only, ≤ 5 MB
- Workbook sheets exactly: `README`, `Course`, `Modules`, `Lessons`, `Quiz`, `Choices` (hidden)
- Column orders exactly as defined in Task 1's header constants — the README, builder, parser, and tests all share them
- Quiz sheet has SEPARATE `module_order` and `lesson_order` columns
- Dropdowns (openpyxl DataValidation, list type, referencing the hidden Choices sheet): Course→`pillar_slug`/`level`/`content_format`; Lessons→`lesson_type`/`required`. Pillar slugs come from the DB at export time
- Import is two-phase: validate fully (row-addressed errors `Sheet!CellRef: message`), then create everything in ONE transaction; on any error nothing is created
- Imported course: unpublished, `created_by` = importer, title suffixed `" (imported)"`/`" (imported N)"` on collision, `CourseEditHistory` change `{'course_imported': {'title': ...}}`
- Round-trip invariant: export → import reproduces identical structure
- Commit after each task, messages ending with the project's Co-Authored-By trailer

---

### Task 1: Workbook builder + export endpoint

**Files:**
- Modify: `backend/pyproject.toml` (add `"openpyxl>=3.1"` to dependencies)
- Create: `backend/hub/xlsx_transfer.py`
- Create: `backend/hub/views/authoring_xlsx.py`
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Test: `backend/hub/tests/test_xlsx_transfer.py` (new)

**Interfaces:**
- Produces: `build_course_workbook(course) -> openpyxl.Workbook`; header constants `COURSE_HEADERS`, `MODULE_HEADERS`, `LESSON_HEADERS`, `QUIZ_HEADERS`, `OPTION_LETTERS`; `GET /api/authoring/courses/<id>/export/` returning an xlsx attachment named `<slug>.xlsx`. Task 2 consumes the constants and the workbook layout.

- [ ] **Step 1: Add the dependency and sync**

Add `"openpyxl>=3.1",` to `[project] dependencies` in `backend/pyproject.toml`, then run from `backend/`: `uv.exe sync` (or `uv.exe pip install openpyxl` if sync is unavailable) and verify `uv.exe run python -c "import openpyxl; print(openpyxl.__version__)"`.

- [ ] **Step 2: Write the failing export tests**

Create `backend/hub/tests/test_xlsx_transfer.py`:

```python
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
```

Run: `uv.exe run manage.py test hub.tests.test_xlsx_transfer -v 2` → expect FAIL (`NoReverseMatch`).

- [ ] **Step 3: Implement `backend/hub/xlsx_transfer.py` (builder half)**

```python
"""Course <-> xlsx workbook conversion. One workbook = one course."""
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from hub.models import Course, LearningPillar, Lesson

COURSE_HEADERS = ['title', 'description', 'pillar_slug', 'level',
                  'duration_hours', 'content_format', 'learning_outcomes']
MODULE_HEADERS = ['order', 'title', 'description', 'duration_minutes']
LESSON_HEADERS = ['module_order', 'order', 'title', 'description',
                  'lesson_type', 'content', 'duration_minutes', 'required']
QUIZ_HEADERS   = ['module_order', 'lesson_order', 'question_order', 'question',
                  'option_a', 'option_b', 'option_c', 'option_d', 'option_e',
                  'option_f', 'correct']
OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']
DROPDOWN_ROWS  = 500

README_LINES = [
    'AIDEA course workbook',
    '',
    'This file describes ONE course. Import it in Authoring -> Import course.',
    'Importing always creates a NEW unpublished draft owned by you.',
    '',
    'Sheets:',
    '  Course  - exactly one row (row 2). pillar_slug, level and content_format',
    '            offer dropdowns. learning_outcomes: one outcome per line in the cell',
    '            (Alt+Enter inside Excel).',
    '  Modules - one row per module. "order" must be a unique positive number.',
    '  Lessons - one row per lesson. module_order refers to the Modules sheet.',
    '            lesson_type and required offer dropdowns.',
    '  Quiz    - one row per question, only for lessons whose type is quiz.',
    '            module_order and lesson_order refer to the Lessons sheet.',
    '            Fill option_a..option_f (at least two) and put the correct',
    '            letter(s) in "correct", comma separated, e.g. B or A,C.',
    '',
    'Do not rename sheets or reorder columns. The hidden Choices sheet feeds',
    'the dropdowns - leave it alone.',
]


def _write_headers(ws, headers):
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)


def _list_validation(wb, ws, choices_col, n_choices, target_col, last_row):
    dv = DataValidation(
        type='list',
        formula1=f'Choices!${choices_col}$1:${choices_col}${n_choices}',
        allow_blank=True,
        showDropDown=False,
    )
    ws.add_data_validation(dv)
    dv.add(f'{target_col}2:{target_col}{last_row}')


def build_course_workbook(course: Course) -> Workbook:
    wb = Workbook()

    readme = wb.active
    readme.title = 'README'
    for i, line in enumerate(README_LINES, start=1):
        readme.cell(row=i, column=1, value=line)
    readme.column_dimensions['A'].width = 90

    # ── Choices (hidden) ────────────────────────────────────────────────
    choices = wb.create_sheet('Choices')
    levels          = [c[0] for c in Course.Level.choices]
    content_formats = [c[0] for c in Course.ContentFormat.choices]
    lesson_types    = [c[0] for c in Lesson.LessonType.choices]
    pillar_slugs    = list(LearningPillar.objects.values_list('slug', flat=True))
    yes_no          = ['yes', 'no']
    for col, values in enumerate([levels, content_formats, lesson_types, pillar_slugs, yes_no], start=1):
        for row, value in enumerate(values, start=1):
            choices.cell(row=row, column=col, value=value)
    choices.sheet_state = 'hidden'

    # ── Course ──────────────────────────────────────────────────────────
    course_ws = wb.create_sheet('Course')
    _write_headers(course_ws, COURSE_HEADERS)
    course_ws.append([
        course.title,
        course.description,
        course.pillar.slug,
        course.level,
        course.duration_hours,
        course.content_format,
        '\n'.join(course.learning_outcomes or []),
    ])
    course_ws['G2'].alignment = course_ws['G2'].alignment.copy(wrap_text=True)
    _list_validation(wb, course_ws, 'D', max(len(pillar_slugs), 1), 'C', 2)
    _list_validation(wb, course_ws, 'A', len(levels), 'D', 2)
    _list_validation(wb, course_ws, 'B', len(content_formats), 'F', 2)

    # ── Modules ─────────────────────────────────────────────────────────
    modules_ws = wb.create_sheet('Modules')
    _write_headers(modules_ws, MODULE_HEADERS)
    modules = list(course.modules.order_by('order').prefetch_related('lessons'))
    for module in modules:
        modules_ws.append([module.order, module.title, module.description, module.duration_minutes])

    # ── Lessons ─────────────────────────────────────────────────────────
    lessons_ws = wb.create_sheet('Lessons')
    _write_headers(lessons_ws, LESSON_HEADERS)
    quiz_rows = []
    for module in modules:
        for lesson in module.lessons.order_by('order'):
            lessons_ws.append([
                module.order,
                lesson.order,
                lesson.title,
                lesson.description,
                lesson.lesson_type,
                lesson.content,
                lesson.duration_minutes,
                'yes' if lesson.is_required else 'no',
            ])
            if lesson.lesson_type == Lesson.LessonType.QUIZ:
                for q_idx, question in enumerate(lesson.quiz_data or [], start=1):
                    options = question.get('options', [])[:len(OPTION_LETTERS)]
                    texts = [opt.get('text', '') for opt in options]
                    texts += [''] * (len(OPTION_LETTERS) - len(texts))
                    correct = ','.join(
                        OPTION_LETTERS[i] for i, opt in enumerate(options)
                        if opt.get('is_correct')
                    )
                    quiz_rows.append([
                        module.order, lesson.order, q_idx,
                        question.get('question', ''), *texts, correct,
                    ])
    _list_validation(wb, lessons_ws, 'C', len(lesson_types), 'E', DROPDOWN_ROWS)
    _list_validation(wb, lessons_ws, 'E', len(yes_no), 'H', DROPDOWN_ROWS)

    # ── Quiz ────────────────────────────────────────────────────────────
    quiz_ws = wb.create_sheet('Quiz')
    _write_headers(quiz_ws, QUIZ_HEADERS)
    for row in quiz_rows:
        quiz_ws.append(row)

    for ws in (course_ws, modules_ws, lessons_ws, quiz_ws):
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

    return wb
```

- [ ] **Step 4: Export view + route**

Create `backend/hub/views/authoring_xlsx.py`:

```python
from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course
from hub.xlsx_transfer import build_course_workbook

from .permissions import IsContentCreator

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class AuthoringCourseExportView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        try:
            course = Course.objects.select_related('pillar').prefetch_related(
                'modules__lessons',
            ).get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        buffer = BytesIO()
        build_course_workbook(course).save(buffer)
        filename = f'{slugify(course.title) or "course"}.xlsx'
        response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

Export `AuthoringCourseExportView` in `backend/hub/views/__init__.py`; route in `backend/hub/urls.py`:

```python
    path('authoring/courses/<int:pk>/export/', AuthoringCourseExportView.as_view(), name='authoring-course-export'),
```

- [ ] **Step 5: Run tests (GREEN), ruff, commit**

`uv.exe run manage.py test hub.tests.test_xlsx_transfer -v 2` → all pass. `uv.exe run ruff check . --fix`.

```bash
git add backend/pyproject.toml backend/uv.lock backend/hub/xlsx_transfer.py backend/hub/views backend/hub/urls.py backend/hub/tests/test_xlsx_transfer.py
git commit -m "feat: export a course as an xlsx workbook with choice dropdowns"
```

---

### Task 2: Workbook parser + import endpoint

**Files:**
- Modify: `backend/hub/xlsx_transfer.py` (parser half)
- Modify: `backend/hub/views/authoring_xlsx.py` (import view)
- Modify: `backend/hub/views/__init__.py`, `backend/hub/urls.py`
- Test: `backend/hub/tests/test_xlsx_transfer.py` (append)

**Interfaces:**
- Consumes: header constants and workbook layout from Task 1
- Produces: `parse_course_workbook(file) -> tuple[dict | None, list[str]]` (payload with course fields + nested modules/lessons/quiz_data, or row-addressed errors); `POST /api/authoring/courses/import/` per the spec

- [ ] **Step 1: Write the failing import tests (append to test_xlsx_transfer.py)**

```python
class ImportXlsxTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='xlsx_imp', password='pass12345')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.teacher = User.objects.create_user(username='xlsx_imp_t', password='pass12345')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)
        self.course = make_course(self.creator, title='Round Trip')
        self.url = reverse('authoring-course-import')

    def _export_bytes(self, course):
        from io import BytesIO as B
        from hub.xlsx_transfer import build_course_workbook
        buf = B()
        build_course_workbook(course).save(buf)
        buf.seek(0)
        return buf

    def _post(self, buf, name='course.xlsx'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        upload = SimpleUploadedFile(
            name, buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        return self.client.post(self.url, {'file': upload}, format='multipart')

    def test_teacher_forbidden(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self._post(self._export_bytes(self.course)).status_code, 403)

    def test_round_trip(self):
        self.client.force_authenticate(self.creator)
        res = self._post(self._export_bytes(self.course))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new = Course.objects.get(pk=res.data['id'])
        self.assertEqual(new.title, 'Round Trip (imported)')  # collision with original
        self.assertFalse(new.is_published)
        self.assertEqual(new.created_by, self.creator)
        self.assertEqual(new.level, self.course.level)
        self.assertEqual(new.learning_outcomes, self.course.learning_outcomes)
        self.assertEqual(new.modules.count(), 2)
        m2 = new.modules.get(order=2)
        quiz = m2.lessons.get(order=1)
        self.assertEqual(quiz.lesson_type, 'quiz')
        self.assertEqual(quiz.quiz_data, [{
            'question': 'Pick two',
            'options': [
                {'text': 'A1', 'is_correct': True},
                {'text': 'B1', 'is_correct': False},
                {'text': 'C1', 'is_correct': True},
            ],
        }])
        video = new.modules.get(order=1).lessons.get(order=2)
        self.assertFalse(video.is_required)

    def test_invalid_lesson_type_rejected_with_cell_ref(self):
        from openpyxl import load_workbook
        buf = self._export_bytes(self.course)
        wb = load_workbook(buf)
        wb['Lessons']['E2'] = 'vido'
        from io import BytesIO as B
        bad = B()
        wb.save(bad)
        bad.seek(0)
        self.client.force_authenticate(self.creator)
        res = self._post(bad)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any('Lessons!E2' in e for e in res.data['errors']))
        self.assertEqual(Course.objects.filter(title__startswith='Round Trip (imported').count(), 0)

    def test_wrong_extension_rejected(self):
        from io import BytesIO as B
        self.client.force_authenticate(self.creator)
        res = self._post(B(b'not a workbook'), name='course.csv')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
```

Run → expect FAIL (`NoReverseMatch`).

- [ ] **Step 2: Implement the parser in `hub/xlsx_transfer.py`**

Append:

```python
MAX_IMPORT_BYTES = 5 * 1024 * 1024

_YES_NO = {'yes': True, 'no': False, '': True, None: True}


def _cell(sheet, col_idx, row):
    return f'{sheet}!{get_column_letter(col_idx)}{row}'


def _rows(ws):
    """Non-empty data rows as (row_number, values) with header-length padding."""
    for row_num, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if any(v not in (None, '') for v in values):
            yield row_num, values


def _as_int(value, default=0):
    if value in (None, ''):
        return default, True
    try:
        return int(value), True
    except (TypeError, ValueError):
        return default, False


def parse_course_workbook(file):  # noqa: C901 - single cohesive validator
    from openpyxl import load_workbook

    errors: list[str] = []
    try:
        wb = load_workbook(file, data_only=True)
    except Exception:
        return None, ['File is not a valid xlsx workbook.']

    for sheet in ('Course', 'Modules', 'Lessons'):
        if sheet not in wb.sheetnames:
            errors.append(f'Missing sheet: {sheet}.')
    if errors:
        return None, errors

    levels          = {c[0] for c in Course.Level.choices}
    content_formats = {c[0] for c in Course.ContentFormat.choices}
    lesson_types    = {c[0] for c in Lesson.LessonType.choices}
    pillar_by_slug  = {p.slug: p for p in LearningPillar.objects.all()}

    # ── Course sheet ────────────────────────────────────────────────────
    course_rows = list(_rows(wb['Course']))
    if not course_rows:
        return None, ['Course!A2: course row is missing.']
    row_num, values = course_rows[0]
    values = list(values) + [None] * (len(COURSE_HEADERS) - len(values))
    title, description, pillar_slug, level, duration_hours, content_format, outcomes = values[:7]

    if not (title or '').strip():
        errors.append(f'{_cell("Course", 1, row_num)}: title is required.')
    if pillar_slug not in pillar_by_slug:
        errors.append(f'{_cell("Course", 3, row_num)}: unknown pillar_slug {pillar_slug!r}.')
    if level not in levels:
        errors.append(f'{_cell("Course", 4, row_num)}: level must be one of {sorted(levels)}.')
    duration_hours, ok = _as_int(duration_hours)
    if not ok:
        errors.append(f'{_cell("Course", 5, row_num)}: duration_hours must be a number.')
    if content_format in (None, ''):
        content_format = Course.ContentFormat.MIXED
    elif content_format not in content_formats:
        errors.append(f'{_cell("Course", 6, row_num)}: content_format must be one of {sorted(content_formats)}.')

    course_payload = {
        'title': (title or '').strip(),
        'description': description or '',
        'pillar': pillar_by_slug.get(pillar_slug),
        'level': level,
        'duration_hours': duration_hours,
        'content_format': content_format,
        'learning_outcomes': [
            line.strip() for line in str(outcomes or '').splitlines() if line.strip()
        ],
    }

    # ── Modules sheet ───────────────────────────────────────────────────
    modules: dict[int, dict] = {}
    for row_num, values in _rows(wb['Modules']):
        values = list(values) + [None] * (len(MODULE_HEADERS) - len(values))
        order, m_title, m_desc, m_minutes = values[:4]
        order, ok = _as_int(order, default=-1)
        if not ok or order < 1:
            errors.append(f'{_cell("Modules", 1, row_num)}: order must be a positive number.')
            continue
        if order in modules:
            errors.append(f'{_cell("Modules", 1, row_num)}: duplicate module order {order}.')
            continue
        if not (m_title or '').strip():
            errors.append(f'{_cell("Modules", 2, row_num)}: title is required.')
            continue
        m_minutes, ok = _as_int(m_minutes)
        if not ok:
            errors.append(f'{_cell("Modules", 4, row_num)}: duration_minutes must be a number.')
        modules[order] = {
            'order': order, 'title': m_title.strip(), 'description': m_desc or '',
            'duration_minutes': m_minutes, 'lessons': {},
        }
    if not modules:
        errors.append('Modules!A2: at least one module is required.')

    # ── Lessons sheet ───────────────────────────────────────────────────
    for row_num, values in _rows(wb['Lessons']):
        values = list(values) + [None] * (len(LESSON_HEADERS) - len(values))
        m_order, order, l_title, l_desc, l_type, content, minutes, required = values[:8]
        m_order, ok = _as_int(m_order, default=-1)
        if not ok or m_order not in modules:
            errors.append(f'{_cell("Lessons", 1, row_num)}: module_order {m_order!r} does not match any module.')
            continue
        order, ok = _as_int(order, default=-1)
        if not ok or order < 1:
            errors.append(f'{_cell("Lessons", 2, row_num)}: order must be a positive number.')
            continue
        if order in modules[m_order]['lessons']:
            errors.append(f'{_cell("Lessons", 2, row_num)}: duplicate lesson order {order} in module {m_order}.')
            continue
        if not (l_title or '').strip():
            errors.append(f'{_cell("Lessons", 3, row_num)}: title is required.')
            continue
        if l_type not in lesson_types:
            errors.append(f'{_cell("Lessons", 5, row_num)}: unknown lesson_type {l_type!r}.')
            continue
        minutes, ok = _as_int(minutes)
        if not ok:
            errors.append(f'{_cell("Lessons", 7, row_num)}: duration_minutes must be a number.')
        req_key = str(required).strip().lower() if required not in (None, '') else ''
        if req_key not in _YES_NO:
            errors.append(f'{_cell("Lessons", 8, row_num)}: required must be yes or no.')
            req_key = ''
        modules[m_order]['lessons'][order] = {
            'order': order, 'title': l_title.strip(), 'description': l_desc or '',
            'lesson_type': l_type, 'content': content or '',
            'duration_minutes': minutes, 'is_required': _YES_NO[req_key],
            'quiz_data': [],
        }

    # ── Quiz sheet (optional) ───────────────────────────────────────────
    if 'Quiz' in wb.sheetnames:
        for row_num, values in _rows(wb['Quiz']):
            values = list(values) + [None] * (len(QUIZ_HEADERS) - len(values))
            m_order, l_order, q_order, question = values[0], values[1], values[2], values[3]
            option_texts, correct = values[4:10], values[10]
            m_order, ok_m = _as_int(m_order, default=-1)
            l_order, ok_l = _as_int(l_order, default=-1)
            lesson = modules.get(m_order, {}).get('lessons', {}).get(l_order) if ok_m and ok_l else None
            if lesson is None:
                errors.append(f'{_cell("Quiz", 1, row_num)}: module_order/lesson_order do not match any lesson.')
                continue
            if lesson['lesson_type'] != Lesson.LessonType.QUIZ:
                errors.append(f'{_cell("Quiz", 2, row_num)}: lesson {m_order}/{l_order} is not a quiz.')
                continue
            if not (question or '').strip():
                errors.append(f'{_cell("Quiz", 4, row_num)}: question is required.')
                continue
            present = {
                OPTION_LETTERS[i]: str(text).strip()
                for i, text in enumerate(option_texts)
                if text not in (None, '') and str(text).strip()
            }
            if len(present) < 2:
                errors.append(f'{_cell("Quiz", 5, row_num)}: at least two options are required.')
                continue
            correct_letters = [
                c.strip().upper() for c in str(correct or '').split(',') if c.strip()
            ]
            invalid = [c for c in correct_letters if c not in present]
            if not correct_letters or invalid:
                errors.append(f'{_cell("Quiz", 11, row_num)}: correct must list letters of filled options, e.g. A,C.')
                continue
            q_order, ok = _as_int(q_order, default=len(lesson['quiz_data']) + 1)
            lesson['quiz_data'].append((q_order, {
                'question': str(question).strip(),
                'options': [
                    {'text': text, 'is_correct': letter in correct_letters}
                    for letter, text in present.items()
                ],
            }))

    if errors:
        return None, errors

    # Sort quiz questions by question_order and strip the sort key
    for module in modules.values():
        for lesson in module['lessons'].values():
            lesson['quiz_data'] = [
                q for _, q in sorted(lesson['quiz_data'], key=lambda pair: pair[0])
            ]

    course_payload['modules'] = [modules[k] for k in sorted(modules)]
    return course_payload, []
```

- [ ] **Step 3: Import view + route**

Append to `backend/hub/views/authoring_xlsx.py`:

```python
class AuthoringCourseImportView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'errors': ['No file provided.']}, status=status.HTTP_400_BAD_REQUEST)
        if not file.name.lower().endswith('.xlsx'):
            return Response({'errors': ['Only .xlsx files are supported.']}, status=status.HTTP_400_BAD_REQUEST)
        if file.size > MAX_IMPORT_BYTES:
            return Response({'errors': ['File too large (max 5 MB).']}, status=status.HTTP_400_BAD_REQUEST)

        payload, errors = parse_course_workbook(file)
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        title = payload['title']
        if Course.objects.filter(title=title).exists():
            candidate, n = f'{title} (imported)', 2
            while Course.objects.filter(title=candidate).exists():
                candidate = f'{title} (imported {n})'
                n += 1
            title = candidate

        with transaction.atomic():
            course = Course.objects.create(
                title=title,
                description=payload['description'],
                pillar=payload['pillar'],
                level=payload['level'],
                duration_hours=payload['duration_hours'],
                content_format=payload['content_format'],
                learning_outcomes=payload['learning_outcomes'],
                is_published=False,
                created_by=request.user,
            )
            for module_data in payload['modules']:
                module = Module.objects.create(
                    course=course,
                    title=module_data['title'],
                    description=module_data['description'],
                    order=module_data['order'],
                    duration_minutes=module_data['duration_minutes'],
                )
                for lesson_data in sorted(module_data['lessons'].values(), key=lambda l: l['order']):
                    Lesson.objects.create(module=module, **{
                        k: lesson_data[k] for k in (
                            'title', 'description', 'lesson_type', 'content',
                            'duration_minutes', 'order', 'is_required', 'quiz_data',
                        )
                    })
            CourseEditHistory.objects.create(
                course=course,
                editor=request.user,
                changes={'course_imported': {'title': course.title}},
            )

        return Response(CourseAuthoringSerializer(course).data, status=status.HTTP_201_CREATED)
```

Extend the file's imports accordingly (`transaction` from `django.db`, `CourseEditHistory`, `Lesson`, `Module` from `hub.models`, `CourseAuthoringSerializer` from `hub.serializers`, `MAX_IMPORT_BYTES`, `parse_course_workbook` from `hub.xlsx_transfer`). Export the view in `views/__init__.py`; route:

```python
    path('authoring/courses/import/', AuthoringCourseImportView.as_view(), name='authoring-course-import'),
```

**Place this path ABOVE `authoring/courses/<int:pk>/`** in urls.py to avoid the int converter shadowing it (it wouldn't match 'import', but keep ordering explicit anyway).

- [ ] **Step 4: Run tests (GREEN), full suite, ruff, commit**

`uv.exe run manage.py test hub.tests.test_xlsx_transfer -v 2` → all pass; `uv.exe run manage.py test hub analytics -v 1` → green; ruff.

```bash
git add backend/hub
git commit -m "feat: import a course from an xlsx workbook with row-addressed validation"
```

---

### Task 3: Authoring UI — Export and Import controls

**Files:**
- Modify: `frontend/src/pages/AuthoringPage.jsx`
- Modify: `frontend/src/pages/AuthoringPage.css`

**Interfaces:**
- Consumes: `GET /api/authoring/courses/<id>/export/` (blob), `POST /api/authoring/courses/import/` (`FormData` field `file`; `400 {errors: []}` or `201 {id, ...}`)

- [ ] **Step 1: Add handlers and state**

Read `AuthoringPage.jsx` first. Add to the main component (`useRef` for the file input; `Download`, `Upload` added to the lucide-react import; `useNavigate` is already used on this page — verify):

```jsx
  const importInputRef = useRef(null)
  const [importErrors, setImportErrors] = useState([])
  const [importing, setImporting] = useState(false)

  const handleExport = async (course) => {
    try {
      const res = await client.get(`/authoring/courses/${course.id}/export/`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `${course.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'course'}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      setImportErrors(['Export failed. Please try again.'])
    }
  }

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setImportErrors([])
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await client.post('/authoring/courses/import/', fd)
      navigate(`/authoring/courses/${res.data.id}`)
    } catch (err) {
      const errors = err.response?.data?.errors
      setImportErrors(Array.isArray(errors) ? errors : ['Import failed. Please try again.'])
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }
```

- [ ] **Step 2: Add the controls to the JSX**

Next to the existing "New course" button (match its container/classes when you read the file):

```jsx
          <button className="authoring-import-btn" onClick={() => importInputRef.current?.click()} disabled={importing}>
            <Upload size={15} /> {importing ? 'Importing…' : 'Import course'}
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept=".xlsx"
            hidden
            onChange={handleImportFile}
          />
```

Error panel directly under the page header / above the course list:

```jsx
      {importErrors.length > 0 && (
        <div className="authoring-import-errors">
          <div className="authoring-import-errors-head">
            <strong>Import failed — fix these and retry:</strong>
            <button onClick={() => setImportErrors([])}>✕</button>
          </div>
          <ul>
            {importErrors.slice(0, 20).map((msg, i) => <li key={i}>{msg}</li>)}
            {importErrors.length > 20 && <li>…and {importErrors.length - 20} more.</li>}
          </ul>
        </div>
      )}
```

Per-course Export action beside the existing Edit/View button in each course row:

```jsx
                  <button
                    className="authoring-export-btn"
                    onClick={(e) => { e.stopPropagation(); handleExport(course) }}
                    title="Export as xlsx"
                  >
                    <Download size={14} /> Export
                  </button>
```

- [ ] **Step 3: CSS (`AuthoringPage.css`)**

```css
.authoring-import-btn,
.authoring-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-border, #d1d5db);
  border-radius: 6px;
  background: #fff;
  font-size: 0.85rem;
  cursor: pointer;
}

.authoring-import-btn:hover,
.authoring-export-btn:hover { background: #f9fafb; }

.authoring-export-btn { padding: 0.3rem 0.6rem; font-size: 0.8rem; }

.authoring-import-errors {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}

.authoring-import-errors-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.authoring-import-errors-head button {
  border: 0;
  background: none;
  cursor: pointer;
  color: inherit;
}

.authoring-import-errors ul { margin: 0; padding-left: 1.2rem; }
```

- [ ] **Step 4: Verify + commit**

`cd frontend && npm run lint && npm run build` — both pass, warning-free.

```bash
git add frontend/src/pages/AuthoringPage.jsx frontend/src/pages/AuthoringPage.css
git commit -m "feat: export and import course xlsx from the authoring page"
```

---

### Final verification

- [ ] `cd backend && uv.exe run coverage run manage.py test hub analytics -v 1` — green, coverage ≥ 70%
- [ ] `uv.exe run ruff check .` — clean
- [ ] `cd frontend && npm run lint && npm run build` — clean
- [ ] Dispatch final whole-branch code review

## Deployment note

`openpyxl` is a new backend dependency — the VM needs an image rebuild: `docker compose up -d --build` (a plain restart won't install it).
