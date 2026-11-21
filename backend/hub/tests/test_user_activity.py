"""The admin per-user activity page (spec 2026-11-21-user-activity-page)."""
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from hub.models import (
    AccessRequest,
    Activity,
    AssignmentSubmission,
    CompetencyChange,
    Course,
    CourseEditHistory,
    Enrollment,
    Feedback,
    LearningPillar,
    LoginRecord,
    Module,
    PathwayCourseChange,
    PlatformAction,
    Resource,
    UserProfile,
)
from hub.models.messaging import Conversation, Message
from hub.models.recommendations import CourseView
from hub.models.tracking import LearningEvent, ResourceVisit


def _at(model, obj, field, when):
    model.objects.filter(pk=obj.pk).update(**{field: when})


class FeedFixture(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user('fa_user', first_name='Maria', last_name='K')
        UserProfile.objects.create(user=self.user)
        self.other = User.objects.create_user('fa_other', first_name='Bob', last_name='L')
        UserProfile.objects.create(user=self.other)
        pillar = LearningPillar.objects.create(name='P', slug='p', description='')
        self.course = Course.objects.create(title='AI basics', pillar=pillar, is_published=True)
        self.module = Module.objects.create(course=self.course, title='M1', order=1)
        self.activity = Activity.objects.create(module=self.module, title='Prompting', order=1)
        self.resource = Resource.objects.create(activity=self.activity, type='video', title='Clip', order=1)

    def visit(self, user, page_key, active, start):
        return ResourceVisit.objects.create(
            user=user, resource=self.resource, activity=self.activity, module=self.module, course=self.course,
            visit_key=uuid.uuid4(), page_key=page_key, started_at=start, last_seen_at=start,
            active_seconds=active)

    def event(self, user, event_type, when, **data):
        return LearningEvent.objects.create(user=user, resource=self.resource, course=self.course,
                                            event_key=uuid.uuid4(), event_type=event_type, occurred_at=when, data=data)

    def login(self, user, when):
        record = LoginRecord.objects.create(user=user, device='desktop', browser='Chrome')
        _at(LoginRecord, record, 'at', when)
        return record


class FeedTests(FeedFixture):
    def test_visits_grouped_per_page(self):
        from hub.user_activity import feed
        page = uuid.uuid4()
        first = self.now - timedelta(minutes=10)
        for i, active in enumerate((120, 60, 60)):
            self.visit(self.user, page, active, first + timedelta(minutes=i))
        self.visit(self.other, uuid.uuid4(), 300, first)
        items, _ = feed(self.user)
        self.assertEqual([i['kind'] for i in items], ['studied'])
        self.assertEqual(items[0]['params']['minutes'], 4)
        self.assertEqual(items[0]['params']['activity'], 'Prompting')
        self.assertEqual(items[0]['at'], first)
        self.assertEqual(items[0]['course'], {'id': self.course.id, 'title': 'AI basics'})

    def test_noise_events_excluded(self):
        from hub.user_activity import feed
        for i, kind in enumerate(('video_play', 'video_seek', 'pdf_open', 'quiz_answer', 'video_ended', 'pdf_download')):
            self.event(self.user, kind, self.now - timedelta(minutes=i))
        self.assertEqual(sorted(i['kind'] for i in feed(self.user)[0]), ['file_downloaded', 'video_finished'])

    def test_each_source_has_its_category(self):
        from hub.user_activity import feed
        t = self.now - timedelta(hours=1)
        self.event(self.user, 'h5p_attempt', t, raw=3, max=5)
        self.event(self.user, 'h5p_error', t)
        enrollment = Enrollment.objects.create(user=self.user, course=self.course, progress_pct=100, completed_at=t)
        _at(Enrollment, enrollment, 'enrolled_at', t - timedelta(days=1))
        AssignmentSubmission.objects.create(user=self.user, lesson=self.activity, text='x')
        CompetencyChange.objects.create(user=self.user, course=self.course, old_score=2, new_score=3, delta=1)
        CourseView.objects.create(user=self.user, course=self.course)
        CourseEditHistory.objects.create(course=self.course, editor=self.user, changes={'module_added': {'title': 'M2'}})
        CourseEditHistory.objects.create(course=self.course, editor=self.user, changes={'title': {'old': 'a', 'new': 'b'}})
        PlatformAction.objects.create(user=self.user, kind='translation_requested', course=self.course,
                                      label='AI basics', details={'language': 'el', 'scope': 'course'})
        PlatformAction.objects.create(user=self.user, kind='role_changed', label='fa_other',
                                      details={'target': 'fa_other', 'old_role': 'teacher', 'new_role': 'admin'})
        conversation = Conversation.objects.create(user_a=self.user, user_b=self.other)
        Message.objects.create(conversation=conversation, sender=self.user, text='secret')
        Feedback.objects.create(user=self.user, category='bug', message='broken')
        AccessRequest.objects.create(user=self.user, message='please')
        self.login(self.user, t)
        pairs = {(i['category'], i['kind']) for i in feed(self.user)[0]}
        self.assertEqual(pairs, {
            ('learning', 'h5p_attempt'), ('learning', 'h5p_error'), ('learning', 'enrolled'),
            ('learning', 'completed'), ('learning', 'assignment_submitted'), ('learning', 'competency_changed'),
            ('learning', 'course_viewed'), ('authoring', 'edit_module_added'), ('authoring', 'edit_course_edited'),
            ('authoring', 'translation_requested'), ('account', 'role_changed'), ('account', 'message_sent'),
            ('account', 'feedback_sent'), ('account', 'access_requested'), ('account', 'signed_in'),
        })
        h5p = next(i for i in feed(self.user)[0] if i['kind'] == 'h5p_attempt')
        self.assertEqual((h5p['params']['score'], h5p['params']['max_score']), (3, 5))

    def test_review_done_by_user(self):
        from hub.user_activity import feed
        AssignmentSubmission.objects.create(user=self.other, lesson=self.activity, text='x', status='approved',
                                            reviewed_by=self.user, reviewed_at=self.now)
        items = feed(self.user)[0]
        self.assertEqual([(i['category'], i['kind']) for i in items], [('reviews', 'assignment_reviewed')])
        self.assertEqual(items[0]['params'], {'learner': 'Bob L', 'outcome': 'approved'})
        self.assertNotIn('assignment_reviewed', [i['kind'] for i in feed(self.other)[0]])

    def test_publish_not_duplicated(self):
        from hub.user_activity import feed
        edit = CourseEditHistory.objects.create(course=self.course, editor=self.user,
                                                changes={'course_published': {'title': 'AI basics'}})
        change = PathwayCourseChange.objects.create(course=self.course, course_title='AI basics',
                                                    change='published', changed_by=self.user)
        _at(CourseEditHistory, edit, 'edited_at', self.now)
        _at(PathwayCourseChange, change, 'changed_at', self.now + timedelta(seconds=2))
        self.assertEqual([i['kind'] for i in feed(self.user)[0]], ['edit_course_published'])

    def test_message_has_no_content_or_recipient(self):
        from hub.user_activity import feed
        conversation = Conversation.objects.create(user_a=self.user, user_b=self.other)
        Message.objects.create(conversation=conversation, sender=self.user, text='secret')
        item = feed(self.user)[0][0]
        self.assertEqual((item['kind'], item['params'], item['text']), ('message_sent', {}, 'Sent a message'))

    def test_deleted_course_uses_label(self):
        from hub.user_activity import feed
        PlatformAction.objects.create(user=self.user, kind='course_deleted', label='Old course')
        item = feed(self.user)[0][0]
        self.assertIn('Old course', item['text'])
        self.assertIsNone(item['course'])

    def test_category_filter(self):
        from hub.user_activity import feed
        self.login(self.user, self.now)
        CourseView.objects.create(user=self.user, course=self.course)
        self.assertEqual({i['category'] for i in feed(self.user, category='account')[0]}, {'account'})

    def test_paging(self):
        from hub.user_activity import feed
        for i in range(120):
            self.login(self.user, self.now - timedelta(minutes=i))
        page1, before = feed(self.user)
        self.assertEqual(len(page1), 50)
        self.assertEqual([i['at'] for i in page1], sorted((i['at'] for i in page1), reverse=True))
        page2, before2 = feed(self.user, before=before)
        self.assertEqual(len(page2), 50)
        self.assertLess(page2[0]['at'], page1[-1]['at'])
        page3, before3 = feed(self.user, before=before2)
        self.assertEqual((len(page3), before3), (20, None))

    def test_same_timestamp_at_boundary(self):
        from hub.user_activity import feed
        for i in range(49):
            self.login(self.user, self.now - timedelta(minutes=i))
        shared = self.now - timedelta(minutes=49)
        for _ in range(3):
            self.login(self.user, shared)
        for i in range(50, 60):
            self.login(self.user, self.now - timedelta(minutes=i))
        page1, before = feed(self.user)
        self.assertEqual(len(page1), 52)
        page2, _ = feed(self.user, before=before)
        self.assertEqual(len(page2), 10)
        self.assertEqual(len(page1) + len(page2), LoginRecord.objects.filter(user=self.user).count())

    def test_limit_none_returns_everything(self):
        from hub.user_activity import feed
        for i in range(70):
            self.login(self.user, self.now - timedelta(minutes=i))
        items, before = feed(self.user, limit=None)
        self.assertEqual((len(items), before), (70, None))


class AdminClientFixture(APITestCase, FeedFixture):
    def setUp(self):
        FeedFixture.setUp(self)
        self.admin = User.objects.create_user('fa_admin')
        UserProfile.objects.create(user=self.admin, user_type=UserProfile.UserType.ADMIN)
        self.client.force_authenticate(self.admin)

    def _url(self, name='admin-user-activity', pk=None):
        return reverse(name, kwargs={'pk': pk or self.user.pk})


class ActivityApiTests(AdminClientFixture):
    def test_admin_gets_all_sections(self):
        from analytics.learning import CourseData, learner_row
        Enrollment.objects.create(user=self.user, course=self.course, progress_pct=40)
        self.login(self.user, self.now)
        res = self.client.get(self._url())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.data), {'summary', 'courses', 'authoring', 'logins', 'feed', 'next_before'})
        cd = CourseData(self.course)
        expected = learner_row(cd, next(e for e in cd.enrollments if e.user_id == self.user.id))
        self.assertEqual(res.data['courses'][0]['status'], expected['status'])
        self.assertEqual(res.data['courses'][0]['progress_pct'], 40)
        self.assertEqual(res.data['summary']['logins_30d'], 1)
        self.assertEqual(len(res.data['logins']), 1)

    def test_authoring_roles(self):
        from hub.models import CourseCollaborator
        authored = Course.objects.create(title='Mine', pillar=self.course.pillar, created_by=self.user)
        CourseCollaborator.objects.create(course=self.course, user=self.user, role='co_editor')
        for _ in range(2):
            CourseEditHistory.objects.create(course=authored, editor=self.user, changes={'module_added': {}})
        CourseEditHistory.objects.create(course=self.course, editor=self.user, changes={'lesson_added': {}})
        rows = {r['title']: r for r in self.client.get(self._url()).data['authoring']}
        self.assertEqual((rows['Mine']['role'], rows['Mine']['edits']), ('author', 2))
        self.assertEqual((rows['AI basics']['role'], rows['AI basics']['edits']), ('co_editor', 1))

    def test_feed_endpoint_pages(self):
        for i in range(60):
            self.login(self.user, self.now - timedelta(minutes=i))
        first = self.client.get(self._url()).data
        self.assertEqual(len(first['feed']), 50)
        page2 = self.client.get(self._url('admin-user-activity-feed'), {'before': first['next_before']}).data
        self.assertEqual((len(page2['items']), page2['next_before']), (10, None))

    def test_bad_params_400(self):
        url = self._url('admin-user-activity-feed')
        self.assertEqual(self.client.get(url, {'before': 'nonsense'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'category': 'x'}).status_code, 400)

    def test_non_admin_403_unknown_404(self):
        creator = User.objects.create_user('fa_creator')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(creator)
        self.assertEqual(self.client.get(self._url()).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self._url(pk=999999)).status_code, 404)

    def test_user_without_profile(self):
        bare = User.objects.create_user('noprof')
        res = self.client.get(self._url(pk=bare.pk))
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data['summary']['role'], res.data['summary']['competency_score']), ('', None))


class ActivityExportTests(AdminClientFixture):
    def test_export_sheets_and_rows(self):
        from io import BytesIO

        from openpyxl import load_workbook

        from hub.user_activity import feed
        Enrollment.objects.create(user=self.user, course=self.course, progress_pct=40)
        for i in range(3):
            self.login(self.user, self.now - timedelta(minutes=i))
        res = self.client.get(self._url('admin-user-activity-export'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheetml', res['Content-Type'])
        self.assertIn('fa_user-activity.xlsx', res['Content-Disposition'])
        wb = load_workbook(BytesIO(res.content))
        self.assertEqual(wb.sheetnames, ['Summary', 'Courses', 'Authoring', 'Activity', 'Logins'])
        self.assertEqual(wb['Activity'].max_row, len(feed(self.user, limit=None)[0]) + 1)
        self.assertEqual([c.value for c in wb['Logins'][1]], ['Time', 'Device', 'Browser'])
        self.assertEqual(wb['Logins'].max_row, 4)

    def test_formula_text_is_neutralised(self):
        from io import BytesIO

        from openpyxl import load_workbook
        self.course.title = '=HYPERLINK("x")'
        self.course.save()
        Enrollment.objects.create(user=self.user, course=self.course)
        wb = load_workbook(BytesIO(self.client.get(self._url('admin-user-activity-export')).content))
        self.assertEqual(wb['Courses']['B2'].value, '\'=HYPERLINK("x")')

    def test_export_admin_only(self):
        creator = User.objects.create_user('fa_creator2')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(creator)
        self.assertEqual(self.client.get(self._url('admin-user-activity-export')).status_code, 403)
