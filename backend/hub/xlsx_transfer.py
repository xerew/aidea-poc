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
