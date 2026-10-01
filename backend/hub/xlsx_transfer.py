"""Course <-> xlsx workbook conversion. One workbook = one course.

Sheets: Course, Modules, Activities, Resources, Quiz, Translations (plus README
and a hidden Choices sheet feeding the dropdowns).
"""
import json

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from hub.models import Course, LearningPillar, Resource, Subject
from hub.translation import LANGUAGE_NAMES

COURSE_HEADERS = [
    'title', 'description', 'pillar_slug', 'level', 'duration_hours', 'content_format',
    'learning_outcomes', 'subjects', 'additional_pillars', 'cross_axis_relevance',
    'target_audience', 'target_audience_other', 'educational_levels',
    'educational_level_other', 'prior_knowledge',
]
MODULE_HEADERS   = ['order', 'title', 'description', 'duration_minutes', 'related_outcomes']
ACTIVITY_HEADERS = ['module_order', 'order', 'title', 'description', 'duration_minutes']
RESOURCE_HEADERS = ['module_order', 'activity_order', 'order', 'type', 'required',
                    'title', 'content', 'url', 'caption', 'instructions']
QUIZ_HEADERS     = ['module_order', 'activity_order', 'resource_order', 'question_order',
                    'question', 'option_a', 'option_b', 'option_c', 'option_d',
                    'option_e', 'option_f', 'correct']
TRANSLATION_HEADERS = ['type', 'module_order', 'activity_order', 'resource_order',
                       'language', 'field', 'value']
TRANSLATION_FIELDS_BY_TYPE = {
    'course': {'title', 'description', 'learning_outcomes', 'cross_axis_relevance',
               'prior_knowledge', 'target_audience_other', 'educational_level_other', 'status'},
    'module': {'title', 'description'},
    'activity': {'title', 'description'},
    'resource': {'title', 'content', 'caption', 'instructions', 'quiz_data'},
}

MEDIA_TYPES    = {'image', 'video', 'pdf'}
OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']
DROPDOWN_ROWS  = 500


def _ser_translation(field, value):
    """Flatten a translated field's value into one cell."""
    if field == 'learning_outcomes':
        return '\n'.join(value or [])
    if field == 'quiz_data':
        return json.dumps(value or [], ensure_ascii=False)
    return value if value is not None else ''


def _deser_translation(field, raw):
    """Parse a Translations cell back into its value. Returns (value, ok)."""
    if field == 'learning_outcomes':
        return [line.strip() for line in str(raw or '').splitlines() if line.strip()], True
    if field == 'quiz_data':
        if raw in (None, ''):
            return [], True
        try:
            return json.loads(raw), True
        except (ValueError, TypeError):
            return [], False
    return str(raw or ''), True


README_LINES = [
    'AIDEA course workbook',
    '',
    'This file describes ONE course. Import it in Authoring -> Import course.',
    'Importing always creates a NEW unpublished draft owned by you.',
    '',
    'Sheets:',
    '  Course     - exactly one row (row 2). pillar_slug, level and content_format',
    '               offer dropdowns. learning_outcomes: one outcome per line in the cell',
    '               (Alt+Enter inside Excel). subjects and additional_pillars:',
    '               comma-separated slugs from the hidden Choices sheet.',
    '               target_audience: teachers and/or school_leaders, comma separated.',
    '               educational_levels: any of primary, lower_secondary,',
    '               upper_secondary, cross_level, comma separated. The *_other',
    '               columns, cross_axis_relevance and prior_knowledge are free text.',
    '  Modules    - one row per module. "order" must be a unique positive number.',
    '               related_outcomes: numbers of the learning outcomes the module',
    '               addresses, comma separated (1 = first outcome), e.g. 1,3.',
    '  Activities - one row per activity. module_order refers to the Modules sheet.',
    '  Resources  - the content of each activity, in order: one row per resource.',
    '               module_order/activity_order refer to the Activities sheet.',
    '               type: text, video, image, pdf, quiz or assignment.',
    '               text uses "content" (HTML allowed); video/image/pdf use "url"',
    '               and an optional "caption"; assignment uses "instructions";',
    '               quiz questions go on the Quiz sheet. required: yes or no.',
    '               Every activity needs at least one resource.',
    '  Quiz       - one row per question of a quiz resource (module_order,',
    '               activity_order, resource_order point to the Resources sheet).',
    '               Fill option_a..option_f (at least two) and put the correct',
    '               letter(s) in "correct", comma separated, e.g. B or A,C.',
    '  Translations - existing translations, one row per field. type is course,',
    '               module, activity or resource; the *_order columns point to the',
    '               other sheets; language is a code (el, fr, ...). Auto-filled on',
    '               export; leave it as-is to keep translations.',
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


def _wrap(ws, coord):
    ws[coord].alignment = ws[coord].alignment.copy(wrap_text=True)


# ══ Export ═══════════════════════════════════════════════════════════════════

def build_course_workbook(course: Course | None = None) -> Workbook:  # noqa: C901 - one sheet per block
    """Build a one-course workbook. With ``course=None`` the sheets, headers,
    dropdowns and README are produced with no data rows — a blank import
    template."""
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
    resource_types  = list(Resource.Type.values)
    pillar_slugs    = list(LearningPillar.objects.values_list('slug', flat=True))
    subject_slugs   = list(Subject.objects.filter(is_active=True).values_list('slug', flat=True))
    yes_no          = ['yes', 'no']
    for col, values in enumerate(
        [levels, content_formats, resource_types, pillar_slugs, yes_no, subject_slugs], start=1,
    ):
        for row, value in enumerate(values, start=1):
            choices.cell(row=row, column=col, value=value)
    choices.sheet_state = 'hidden'

    # ── Course ──────────────────────────────────────────────────────────
    course_ws = wb.create_sheet('Course')
    _write_headers(course_ws, COURSE_HEADERS)
    translation_rows = []
    if course is not None:
        course_ws.append([
            course.title,
            course.description,
            course.pillar.slug,
            course.level,
            course.duration_hours,
            course.content_format,
            '\n'.join(course.learning_outcomes or []),
            ','.join(course.subjects.values_list('slug', flat=True)),
            ','.join(course.additional_pillars.order_by('order').values_list('slug', flat=True)),
            course.cross_axis_relevance,
            ','.join(course.target_audience or []),
            course.target_audience_other,
            ','.join(course.educational_levels or []),
            course.educational_level_other,
            course.prior_knowledge,
        ])
        for coord in ('G2', 'J2', 'O2'):
            _wrap(course_ws, coord)
        for lang, st in (course.translation_status or {}).items():
            translation_rows.append(['course', '', '', '', lang, 'status', st])
        for lang, blob in (course.translations or {}).items():
            for field in sorted(TRANSLATION_FIELDS_BY_TYPE['course'] - {'status'}):
                if field in blob:
                    translation_rows.append(['course', '', '', '', lang, field, _ser_translation(field, blob[field])])
    _list_validation(wb, course_ws, 'D', max(len(pillar_slugs), 1), 'C', 2)
    _list_validation(wb, course_ws, 'A', len(levels), 'D', 2)
    _list_validation(wb, course_ws, 'B', len(content_formats), 'F', 2)

    # ── Modules ─────────────────────────────────────────────────────────
    modules_ws = wb.create_sheet('Modules')
    _write_headers(modules_ws, MODULE_HEADERS)
    modules = (
        list(course.modules.order_by('order').prefetch_related('lessons__resources'))
        if course else []
    )
    for module in modules:
        modules_ws.append([
            module.order, module.title, module.description, module.duration_minutes,
            ','.join(str(i + 1) for i in (module.related_outcomes or [])),
        ])
        for lang, blob in (module.translations or {}).items():
            for field in ('title', 'description'):
                if field in blob:
                    translation_rows.append(['module', module.order, '', '', lang, field,
                                             _ser_translation(field, blob[field])])

    # ── Activities, Resources, Quiz ─────────────────────────────────────
    activities_ws = wb.create_sheet('Activities')
    _write_headers(activities_ws, ACTIVITY_HEADERS)
    resources_ws = wb.create_sheet('Resources')
    _write_headers(resources_ws, RESOURCE_HEADERS)
    quiz_rows = []
    for module in modules:
        for activity in sorted(module.lessons.all(), key=lambda a: a.order):
            activities_ws.append([
                module.order, activity.order, activity.title, activity.description,
                activity.duration_minutes,
            ])
            for lang, blob in (activity.translations or {}).items():
                for field in ('title', 'description'):
                    if blob.get(field):
                        translation_rows.append(['activity', module.order, activity.order, '', lang,
                                                 field, _ser_translation(field, blob[field])])
            # Number resources by position so the sheet's keys are always unique.
            for r_order, resource in enumerate(sorted(activity.resources.all(), key=lambda r: r.order), start=1):
                resources_ws.append([
                    module.order, activity.order, r_order, resource.type,
                    'yes' if resource.is_required else 'no',
                    resource.title, resource.content, resource.url, resource.caption,
                    resource.instructions,
                ])
                for lang, blob in (resource.translations or {}).items():
                    for field in sorted(TRANSLATION_FIELDS_BY_TYPE['resource']):
                        if blob.get(field):
                            translation_rows.append(['resource', module.order, activity.order, r_order,
                                                     lang, field, _ser_translation(field, blob[field])])
                if resource.type == Resource.Type.QUIZ:
                    for q_idx, question in enumerate(resource.quiz_data or [], start=1):
                        options = question.get('options', [])[:len(OPTION_LETTERS)]
                        texts = [opt.get('text', '') for opt in options]
                        texts += [''] * (len(OPTION_LETTERS) - len(texts))
                        correct = ','.join(
                            OPTION_LETTERS[i] for i, opt in enumerate(options) if opt.get('is_correct')
                        )
                        quiz_rows.append([
                            module.order, activity.order, r_order, q_idx,
                            question.get('question', ''), *texts, correct,
                        ])
    _list_validation(wb, resources_ws, 'C', len(resource_types), 'D', DROPDOWN_ROWS)
    _list_validation(wb, resources_ws, 'E', len(yes_no), 'E', DROPDOWN_ROWS)

    quiz_ws = wb.create_sheet('Quiz')
    _write_headers(quiz_ws, QUIZ_HEADERS)
    for row in quiz_rows:
        quiz_ws.append(row)

    # ── Translations ────────────────────────────────────────────────────
    translations_ws = wb.create_sheet('Translations')
    _write_headers(translations_ws, TRANSLATION_HEADERS)
    for row in translation_rows:
        translations_ws.append(row)

    for ws in (course_ws, modules_ws, activities_ws, resources_ws, quiz_ws, translations_ws):
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

    return wb


# ══ Import ═══════════════════════════════════════════════════════════════════

MAX_IMPORT_BYTES = 5 * 1024 * 1024

_YES_NO = {'yes': True, 'no': False, '': True, None: True}

# PositiveSmallIntegerField maps to Postgres smallint: CHECK (>= 0), max 32767.
# Values outside this range must fail phase-1 validation, not blow up the insert.
INT_MAX = 32767


def _cell(sheet, col_idx, row):
    return f'{sheet}!{get_column_letter(col_idx)}{row}'


def _rows(ws, width):
    """Non-empty data rows as (row_number, values padded to `width`)."""
    for row_num, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if any(v not in (None, '') for v in values):
            yield row_num, list(values) + [None] * (width - len(values))


def _as_int(value, default=0):
    if value in (None, ''):
        return default, True
    if isinstance(value, float) and not value.is_integer():
        return default, False
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default, False
    if not 0 <= number <= INT_MAX:
        return default, False
    return number, True


def _tokens(raw):
    """Comma/semicolon/newline-separated cell → lower-cased tokens."""
    text = str(raw or '').replace(';', ',').replace('\n', ',')
    return [t.strip().lower() for t in text.split(',') if t.strip()]


def _yes_no(raw, sheet, col, row_num, errors):
    key = str(raw).strip().lower() if raw not in (None, '') else ''
    if key not in _YES_NO:
        errors.append(f'{_cell(sheet, col, row_num)}: required must be yes or no.')
        key = ''
    return _YES_NO[key]


def _parse_quiz_row(values, start, sheet, row_num, errors):
    """Parse question + options + correct letters beginning at column index
    `start` (the question). Returns the question dict or None on error."""
    question = values[start]
    option_texts, correct = values[start + 1:start + 7], values[start + 7]
    if not (question or '').strip():
        errors.append(f'{_cell(sheet, start + 1, row_num)}: question is required.')
        return None
    present = {
        OPTION_LETTERS[i]: str(text).strip()
        for i, text in enumerate(option_texts)
        if text not in (None, '') and str(text).strip()
    }
    if len(present) < 2:
        errors.append(f'{_cell(sheet, start + 2, row_num)}: at least two options are required.')
        return None
    correct_letters = [c.strip().upper() for c in str(correct or '').split(',') if c.strip()]
    if not correct_letters or any(c not in present for c in correct_letters):
        errors.append(f'{_cell(sheet, start + 8, row_num)}: correct must list letters of filled options, e.g. A,C.')
        return None
    return {
        'question': str(question).strip(),
        'options': [
            {'text': text, 'is_correct': letter in correct_letters}
            for letter, text in present.items()
        ],
    }


def _sorted_values(pairs):
    return [item for _, item in sorted(pairs, key=lambda pair: pair[0])]


def parse_course_workbook(file):
    """Validate a workbook. Returns (payload, []) or (None, errors)."""
    from openpyxl import load_workbook

    try:
        wb = load_workbook(file, data_only=True)
    except Exception:
        return None, ['File is not a valid xlsx workbook.']

    required = ('Course', 'Modules', 'Activities', 'Resources')
    errors = [f'Missing sheet: {sheet}.' for sheet in required if sheet not in wb.sheetnames]
    if errors:
        return None, errors

    course_payload = _parse_course_sheet(wb, errors)
    if course_payload is None:
        return None, errors
    modules = _parse_modules_sheet(wb, course_payload, errors)
    _parse_content_sheets(wb, modules, course_payload, errors)

    if errors:
        return None, errors
    course_payload['modules'] = [modules[k] for k in sorted(modules)]
    return course_payload, []


def _parse_course_sheet(wb, errors):  # noqa: C901 - flat field-by-field validation
    levels          = {c[0] for c in Course.Level.choices}
    content_formats = {c[0] for c in Course.ContentFormat.choices}
    pillar_by_slug  = {p.slug: p for p in LearningPillar.objects.all()}
    subject_by_slug = {s.slug: s for s in Subject.objects.filter(is_active=True)}

    course_rows = list(_rows(wb['Course'], len(COURSE_HEADERS)))
    if not course_rows:
        errors.append('Course!A2: course row is missing.')
        return None
    row_num, values = course_rows[0]
    (title, description, pillar_slug, level, duration_hours, content_format, outcomes, subjects,
     extra_pillars, cross_axis, audience, audience_other, edu_levels, edu_other, prior) = values[:15]

    subject_objs = []
    for slug in _tokens(subjects):
        if slug not in subject_by_slug:
            errors.append(f'{_cell("Course", 8, row_num)}: unknown subject slug {slug!r}.')
        else:
            subject_objs.append(subject_by_slug[slug])

    extra_pillar_objs = []
    for slug in _tokens(extra_pillars):
        if slug not in pillar_by_slug:
            errors.append(f'{_cell("Course", 9, row_num)}: unknown pillar slug {slug!r}.')
        elif slug != pillar_slug:  # the primary pillar is never also an additional one
            extra_pillar_objs.append(pillar_by_slug[slug])

    def _choice_list(raw, allowed, col, name):
        picked = _tokens(raw)
        bad = [v for v in picked if v not in allowed]
        if bad:
            errors.append(f'{_cell("Course", col, row_num)}: {name} must be from {allowed}, got {bad}.')
        return [v for v in allowed if v in picked]

    if not (title or '').strip():
        errors.append(f'{_cell("Course", 1, row_num)}: title is required.')
    if pillar_slug not in pillar_by_slug:
        errors.append(f'{_cell("Course", 3, row_num)}: unknown pillar_slug {pillar_slug!r}.')
    if level not in levels:
        errors.append(f'{_cell("Course", 4, row_num)}: level must be one of {sorted(levels)}.')
    duration_hours, ok = _as_int(duration_hours)
    if not ok:
        errors.append(f'{_cell("Course", 5, row_num)}: duration_hours must be a whole number between 0 and 32767.')
    if content_format in (None, ''):
        content_format = Course.ContentFormat.MIXED
    elif content_format not in content_formats:
        errors.append(f'{_cell("Course", 6, row_num)}: content_format must be one of {sorted(content_formats)}.')

    return {
        'title': (title or '').strip(),
        'description': description or '',
        'pillar': pillar_by_slug.get(pillar_slug),
        'level': level,
        'duration_hours': duration_hours,
        'content_format': content_format,
        'learning_outcomes': [line.strip() for line in str(outcomes or '').splitlines() if line.strip()],
        'subjects': subject_objs,
        'additional_pillars': extra_pillar_objs,
        'cross_axis_relevance': str(cross_axis or ''),
        'target_audience': _choice_list(audience, Course.AUDIENCE_CHOICES, 11, 'target_audience'),
        'target_audience_other': str(audience_other or '')[:200],
        'educational_levels': _choice_list(edu_levels, Course.EDUCATIONAL_LEVEL_CHOICES, 13, 'educational_levels'),
        'educational_level_other': str(edu_other or '')[:200],
        'prior_knowledge': str(prior or ''),
        'translations': {},
        'translation_status': {},
    }


def _parse_modules_sheet(wb, course_payload, errors):
    outcome_count = len(course_payload['learning_outcomes'])
    modules: dict[int, dict] = {}
    for row_num, values in _rows(wb['Modules'], len(MODULE_HEADERS)):
        order, m_title, m_desc, m_minutes, m_outcomes = values[:5]
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
            errors.append(f'{_cell("Modules", 4, row_num)}: duration_minutes must be a whole number between 0 and 32767.')
        related = set()
        for token in _tokens(m_outcomes):
            number, ok = _as_int(token, default=-1)
            if not ok or not 1 <= number <= outcome_count:
                errors.append(
                    f'{_cell("Modules", 5, row_num)}: related_outcomes must be outcome numbers '
                    f'between 1 and {outcome_count}, got {token!r}.'
                )
                continue
            related.add(number - 1)
        modules[order] = {
            'order': order, 'title': m_title.strip(), 'description': m_desc or '',
            'duration_minutes': m_minutes, 'related_outcomes': sorted(related),
            'activities': {}, 'translations': {},
        }
    if not modules:
        errors.append('Modules!A2: at least one module is required.')
    return modules


def _parse_content_sheets(wb, modules, course_payload, errors):  # noqa: C901 - one block per sheet
    # ── Activities ──────────────────────────────────────────────────────
    activity_rows = {}
    for row_num, values in _rows(wb['Activities'], len(ACTIVITY_HEADERS)):
        m_order, order, a_title, a_desc, minutes = values[:5]
        m_order, ok = _as_int(m_order, default=-1)
        if not ok or m_order not in modules:
            errors.append(f'{_cell("Activities", 1, row_num)}: module_order {m_order!r} does not match any module.')
            continue
        order, ok = _as_int(order, default=-1)
        if not ok or order < 1:
            errors.append(f'{_cell("Activities", 2, row_num)}: order must be a positive number.')
            continue
        activities = modules[m_order]['activities']
        if order in activities:
            errors.append(f'{_cell("Activities", 2, row_num)}: duplicate activity order {order} in module {m_order}.')
            continue
        if not (a_title or '').strip():
            errors.append(f'{_cell("Activities", 3, row_num)}: title is required.')
            continue
        minutes, ok = _as_int(minutes)
        if not ok:
            errors.append(f'{_cell("Activities", 5, row_num)}: duration_minutes must be a whole number between 0 and 32767.')
        activities[order] = {
            'order': order, 'title': a_title.strip(), 'description': a_desc or '',
            'duration_minutes': minutes, 'resources': {}, 'translations': {},
        }
        activity_rows[(m_order, order)] = row_num

    def _activity(m_order, a_order):
        m_order, ok_m = _as_int(m_order, default=-1)
        a_order, ok_a = _as_int(a_order, default=-1)
        if not (ok_m and ok_a):
            return None
        return modules.get(m_order, {}).get('activities', {}).get(a_order)

    # ── Resources ───────────────────────────────────────────────────────
    resource_types = set(Resource.Type.values)
    for row_num, values in _rows(wb['Resources'], len(RESOURCE_HEADERS)):
        m_order, a_order, order, r_type, required, r_title, content, url, caption, instructions = values[:10]
        activity = _activity(m_order, a_order)
        if activity is None:
            errors.append(f'{_cell("Resources", 1, row_num)}: module_order/activity_order do not match any activity.')
            continue
        order, ok = _as_int(order, default=-1)
        if not ok or order < 1:
            errors.append(f'{_cell("Resources", 3, row_num)}: order must be a positive number.')
            continue
        if order in activity['resources']:
            errors.append(f'{_cell("Resources", 3, row_num)}: duplicate resource order {order} in this activity.')
            continue
        if r_type not in resource_types:
            errors.append(f'{_cell("Resources", 4, row_num)}: type must be one of {sorted(resource_types)}.')
            continue
        url = str(url or '').strip()
        if r_type in MEDIA_TYPES and not url:
            errors.append(f'{_cell("Resources", 8, row_num)}: url is required for {r_type} resources.')
            continue
        activity['resources'][order] = {
            'order': order, 'type': r_type,
            'is_required': _yes_no(required, 'Resources', 5, row_num, errors),
            'title': str(r_title or '')[:200], 'content': str(content or ''),
            'url': url[:500], 'caption': str(caption or '')[:300],
            'instructions': str(instructions or ''), 'quiz_data': [], 'translations': {},
        }

    for (m_order, a_order), row_num in activity_rows.items():
        if not modules[m_order]['activities'][a_order]['resources']:
            errors.append(f'{_cell("Activities", 1, row_num)}: activity has no resources on the Resources sheet.')

    def _resource(m_order, a_order, r_order):
        activity = _activity(m_order, a_order)
        r_order, ok = _as_int(r_order, default=-1)
        return activity['resources'].get(r_order) if activity and ok else None

    # ── Quiz ────────────────────────────────────────────────────────────
    if 'Quiz' in wb.sheetnames:
        for row_num, values in _rows(wb['Quiz'], len(QUIZ_HEADERS)):
            resource = _resource(values[0], values[1], values[2])
            if resource is None:
                errors.append(f'{_cell("Quiz", 1, row_num)}: module/activity/resource order do not match any resource.')
                continue
            if resource['type'] != Resource.Type.QUIZ:
                errors.append(f'{_cell("Quiz", 3, row_num)}: that resource is not a quiz.')
                continue
            question = _parse_quiz_row(values, 4, 'Quiz', row_num, errors)
            if question is not None:
                q_order, _ = _as_int(values[3], default=len(resource['quiz_data']) + 1)
                resource['quiz_data'].append((q_order, question))
        for module in modules.values():
            for activity in module['activities'].values():
                for resource in activity['resources'].values():
                    resource['quiz_data'] = _sorted_values(resource['quiz_data'])

    # ── Translations ────────────────────────────────────────────────────
    if 'Translations' in wb.sheetnames:
        for row_num, values in _rows(wb['Translations'], len(TRANSLATION_HEADERS)):
            t_type, m_order, a_order, r_order, language, field, value = values[:7]
            t_type = str(t_type or '').strip().lower()
            language = str(language or '').strip()
            field = str(field or '').strip()
            if t_type not in TRANSLATION_FIELDS_BY_TYPE:
                errors.append(f'{_cell("Translations", 1, row_num)}: type must be course, module, activity or resource.')
                continue
            if language not in LANGUAGE_NAMES:
                errors.append(f'{_cell("Translations", 5, row_num)}: unknown language {language!r}.')
                continue
            if field not in TRANSLATION_FIELDS_BY_TYPE[t_type]:
                errors.append(f'{_cell("Translations", 6, row_num)}: unknown {t_type} field {field!r}.')
                continue
            if t_type == 'course':
                if field == 'status':
                    course_payload['translation_status'][language] = str(value or '').strip()
                    continue
                owner = course_payload
            elif t_type == 'module':
                number, ok = _as_int(m_order, default=-1)
                owner = modules.get(number) if ok else None
            elif t_type == 'activity':
                owner = _activity(m_order, a_order)
            else:
                owner = _resource(m_order, a_order, r_order)
            if owner is None:
                errors.append(f'{_cell("Translations", 2, row_num)}: the *_order columns do not match any {t_type}.')
                continue
            parsed, ok = _deser_translation(field, value)
            if not ok:
                errors.append(f'{_cell("Translations", 7, row_num)}: {field} value is not valid.')
                continue
            owner['translations'].setdefault(language, {})[field] = parsed

