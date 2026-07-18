# Course Export/Import via xlsx — Design

Approved decisions (user): one course per file; import always creates a new
unpublished draft owned by the importer; every platform choice-set is an
in-cell dropdown in the workbook; Quiz sheet uses separate `module_order`
and `lesson_order` columns.

## Workbook format

One `.xlsx` file = one course. Filename on export: `<slugified-title>.xlsx`.

| Sheet | Row semantics |
|---|---|
| README | Instructions: column docs, allowed values, quiz format, import behavior. First sheet, read-only intent. |
| Course | Exactly one data row (row 2). |
| Modules | One row per module. |
| Lessons | One row per lesson. |
| Quiz | One row per quiz question. |
| Choices | Hidden sheet holding dropdown lists (levels, content formats, lesson types, pillar slugs, yes/no). |

### Columns

**Course** (row 2): `title` (required), `description`, `pillar_slug`
(dropdown, required), `level` (dropdown, required), `duration_hours` (int,
default 0), `content_format` (dropdown, default mixed), `learning_outcomes`
(one outcome per line inside the cell).

**Modules**: `order` (unique positive int, required), `title` (required),
`description`, `duration_minutes` (int, default 0).

**Lessons**: `module_order` (must match a Modules row), `order` (unique
within module), `title` (required), `description`, `lesson_type` (dropdown,
required), `content` (text body or URL depending on type), `duration_minutes`
(int, default 0), `required` (dropdown yes/no, default yes).

**Quiz**: `module_order`, `lesson_order` (separate columns; must resolve to
a Lessons row with `lesson_type=quiz`), `question_order` (unique within
lesson), `question` (required), `option_a`…`option_f` (≥2 non-empty),
`correct` (comma-separated letters, e.g. `B` or `A,C`; every letter must
point at a non-empty option; ≥1 required). Free text, not a dropdown —
multi-select isn't expressible as Excel list validation; validated on import.

### Dropdowns

openpyxl `DataValidation` (type="list") applied to generous row ranges
(rows 2–500) on the relevant columns, with formulas referencing the hidden
Choices sheet. Pillar slugs are read live from `LearningPillar` at export
time, so new pillars automatically appear.

## API

Both endpoints `IsContentCreator`.

- `GET /api/authoring/courses/<id>/export/` → the workbook as an
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  attachment. Any content creator may export any course (authoring reads
  are open).
- `POST /api/authoring/courses/import/` — multipart field `file`, `.xlsx`
  only, ≤ 5 MB. Two-phase: **validate everything, then create everything**
  in one transaction. On any validation error: `400 {"errors": ["Sheet!Cell:
  message", ...]}` and nothing is created. On success: `201` with the new
  course's authoring payload; course is unpublished, `created_by` =
  importer, title suffixed `" (imported)"` when the title already exists;
  `CourseEditHistory` entry `course_imported`.

## Implementation shape

- New module `backend/hub/xlsx_transfer.py`: `build_course_workbook(course)
  -> openpyxl.Workbook` and `parse_course_workbook(django_file) ->
  (payload dict | None, errors list)`. Views stay thin.
- New dependency: `openpyxl` in backend/pyproject.toml.
- Round-trip invariant (core test): export any course, import the file →
  identical structure (course fields, module/lesson orders and fields,
  quiz_data including multi-correct options).

## Frontend (Authoring page)

- Per-course "Export" action (Download icon): fetches the endpoint with
  `responseType: 'blob'`, triggers a browser download.
- "Import course" button beside course creation: hidden file input → POST
  FormData → on 400 render the row-addressed error list in a dismissible
  panel; on success navigate to `/authoring/courses/<new id>`.

## Out of scope

Updating existing courses from a file, multi-course workbooks, exports for
teachers/admins, csv.
