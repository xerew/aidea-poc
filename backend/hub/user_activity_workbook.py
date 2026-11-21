"""One person's activity as an Excel workbook (admin per-user activity page)."""
from openpyxl import Workbook
from openpyxl.styles import Font

from analytics.workbook import _append, blank, iso, yes_no
from hub.user_activity import authoring_rows, course_rows, feed, login_rows, summary

SHEETS = (
    ('Summary', ['Field', 'Value']),
    ('Courses', ['Course ID', 'Course', 'Pillar', 'Progress %', 'Active minutes', 'Status', 'Enrolled',
                 'Last active', 'Completed']),
    ('Authoring', ['Course ID', 'Course', 'Role', 'Published', 'Edits']),
    ('Activity', ['Time', 'Category', 'Kind', 'Description', 'Course ID', 'Course']),
    ('Logins', ['Time', 'Device', 'Browser']),
)

SUMMARY_LABELS = (
    ('id', 'User ID'), ('name', 'Name'), ('username', 'Username'), ('email', 'Email'), ('role', 'Role'),
    ('joined', 'Joined'), ('last_login', 'Last login'), ('onboarding_completed', 'Onboarding completed'),
    ('competency_score', 'AI competency score'), ('total_active_s', 'Total active minutes'),
    ('logins_30d', 'Logins in the last 30 days'),
)


def _summary_value(key, value):
    if key in ('joined', 'last_login'):
        return iso(value)
    if key == 'onboarding_completed':
        return yes_no(value)
    if key == 'total_active_s':
        return round((value or 0) / 60)
    return blank(value)


def build_user_workbook(user):
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {}
    for name, headers in SHEETS:
        ws = wb.create_sheet(name)
        _append(ws, headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        sheets[name] = ws

    info = summary(user)
    for key, label in SUMMARY_LABELS:
        _append(sheets['Summary'], [label, _summary_value(key, info[key])])
    for r in course_rows(user):
        _append(sheets['Courses'], [r['course_id'], r['title'], r['pillar'], r['progress_pct'],
                                    round((r['active_s'] or 0) / 60), r['status'], iso(r['enrolled_at']),
                                    iso(r['last_active']), iso(r['completed_at'])])
    for r in authoring_rows(user):
        _append(sheets['Authoring'], [r['course_id'], r['title'], r['role'], yes_no(r['is_published']), r['edits']])
    for item in feed(user, limit=None)[0]:
        course = item['course'] or {}
        _append(sheets['Activity'], [iso(item['at']), item['category'], item['kind'], item['text'],
                                     blank(course.get('id')), course.get('title', '')])
    for r in login_rows(user):
        _append(sheets['Logins'], [iso(r['at']), r['device'], r['browser']])
    return wb
