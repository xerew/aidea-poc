"""One course and six learners shared by the learning-analytics tests.

M1 Basics:   A1 "Read and watch" (text, video) · A2 "Check" (quiz, 2 questions)
M2 Practice: A3 "Apply" (pdf, optional assignment)

ada — active: two page visits on the text (completed), part of the video
bo  — finished the course; quiz answered with timings; PDF opened + downloaded
cy  — inactive: last seen 20 days ago on the video
di  — stuck: 3 visits to the video without finishing it
ev  — stuck: failed the quiz
old — completed the text before tracking began (no visits)
"""
import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from hub.models import (
    Activity,
    AssignmentSubmission,
    Course,
    Enrollment,
    LearningEvent,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    ResourceVisit,
    StudyParticipant,
    UserProfile,
)

NOW = timezone.now()
AGO = NOW - timedelta(minutes=30)


def make_user(username, user_type=UserProfile.UserType.TEACHER, first='', last=''):
    user = User.objects.create_user(
        username=username, password='pass12345', email=f'{username}@example.org',
        first_name=first, last_name=last,
    )
    UserProfile.objects.create(user=user, user_type=user_type)
    return user


def enroll(user, course, days_ago=0, **fields):
    enrollment = Enrollment.objects.create(user=user, course=course, **fields)
    Enrollment.objects.filter(pk=enrollment.pk).update(enrolled_at=NOW - timedelta(days=days_ago))
    enrollment.refresh_from_db()
    return enrollment


def add_visit(user, resource, *, page=None, start=None, active=0, visible=0, **fields):
    start = start or NOW - timedelta(hours=1)
    return ResourceVisit.objects.create(
        user=user, resource=resource, activity=resource.activity,
        module=resource.activity.module, course=resource.activity.module.course,
        visit_key=uuid.uuid4(), page_key=page or uuid.uuid4(),
        started_at=start, last_seen_at=start + timedelta(seconds=visible),
        active_seconds=active, visible_seconds=visible, **fields,
    )


def add_event(user, resource, event_type, at=None, **data):
    return LearningEvent.objects.create(
        user=user, resource=resource, course=resource.activity.module.course,
        event_key=uuid.uuid4(), event_type=event_type, occurred_at=at or AGO, data=data,
    )


def complete(user, resource, at=None, **fields):
    progress = ResourceProgress.objects.create(
        user=user, resource=resource, completed_at=at or AGO, **fields,
    )
    ResourceProgress.objects.filter(pk=progress.pk).update(updated_at=at or AGO)
    return progress


class CourseFixture:
    def __init__(self):
        self.creator = make_user('la_creator', UserProfile.UserType.CONTENT_CREATOR)
        pillar = LearningPillar.objects.create(name='P', slug='p-la', order=1)
        self.course = Course.objects.create(
            title='Analytics Course', pillar=pillar, level='beginner', duration_hours=1,
            is_published=True, created_by=self.creator,
        )
        self.m1 = Module.objects.create(course=self.course, title='Basics', order=1)
        self.m2 = Module.objects.create(course=self.course, title='Practice', order=2)
        self.a1 = Activity.objects.create(module=self.m1, title='Read and watch', order=1)
        self.a2 = Activity.objects.create(module=self.m1, title='Check', order=2)
        self.a3 = Activity.objects.create(module=self.m2, title='Apply', order=1)
        self.text = Resource.objects.create(activity=self.a1, type='text', order=1, title='Intro')
        self.video = Resource.objects.create(activity=self.a1, type='video', order=2, title='Clip')
        self.quiz = Resource.objects.create(activity=self.a2, type='quiz', order=1, title='Quiz', quiz_data=[
            {'question': 'Q one', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]},
            {'question': 'Q two', 'options': [{'text': 'c', 'is_correct': False}, {'text': 'd', 'is_correct': True}]},
        ])
        self.pdf = Resource.objects.create(activity=self.a3, type='pdf', order=1, title='Sheet')
        self.assign = Resource.objects.create(
            activity=self.a3, type='assignment', order=2, title='Task', is_required=False,
        )

        self.ada = make_user('ada', first='Ada', last='Byte')
        self.ada_enr = enroll(self.ada, self.course, progress_pct=0)
        StudyParticipant.objects.create(user=self.ada, in_study=True, consented_at=NOW)
        page1, page2 = uuid.uuid4(), uuid.uuid4()
        add_visit(self.ada, self.text, page=page1, start=NOW - timedelta(hours=3), active=100, visible=120)
        add_visit(self.ada, self.video, page=page1, start=NOW - timedelta(hours=3), active=200, visible=210,
                  media_progress={'covered_pct': 40, 'furthest_s': 120, 'duration_s': 300})
        add_visit(self.ada, self.text, page=page2, start=NOW - timedelta(hours=1), active=50, visible=60,
                  completed_during=True, language='el', device='mobile', local_hour=14, tz_offset_minutes=180)
        complete(self.ada, self.text, engagement_data={'scroll_pct': 80})
        add_event(self.ada, self.video, 'video_play', position=0)
        add_event(self.ada, self.video, 'video_seek', **{'from': 30, 'to': 90})

        self.bo = make_user('bo', first='Bo', last='Bit')
        self.bo_enr = enroll(self.bo, self.course, progress_pct=100, completed_at=NOW - timedelta(days=1))
        add_visit(self.bo, self.text, active=300, visible=320)
        complete(self.bo, self.text)
        complete(self.bo, self.video)
        complete(self.bo, self.quiz, quiz_score=1.0, quiz_answers=[True, True],
                 engagement_data={'quiz_selected': [0, 1]})
        complete(self.bo, self.pdf)
        add_event(self.bo, self.quiz, 'quiz_answer', question_index=0, selected=0, seconds_on_question=12.5)
        add_event(self.bo, self.quiz, 'quiz_answer', question_index=1, selected=1, seconds_on_question=7.5)
        add_event(self.bo, self.pdf, 'pdf_open')
        add_event(self.bo, self.pdf, 'pdf_download')
        AssignmentSubmission.objects.create(
            user=self.bo, lesson=self.a3, resource=self.assign, text='done',
            status=AssignmentSubmission.Status.APPROVED,
        )

        self.cy = make_user('cy')
        self.cy_enr = enroll(self.cy, self.course, days_ago=30)
        add_visit(self.cy, self.video, start=NOW - timedelta(days=20), active=30, visible=40,
                  media_progress={'covered_pct': 10, 'furthest_s': 30, 'duration_s': 300})

        self.di = make_user('di')
        self.di_enr = enroll(self.di, self.course)
        for hours in (5, 4, 3):
            add_visit(self.di, self.video, start=NOW - timedelta(hours=hours), active=20, visible=25)

        self.ev = make_user('ev')
        self.ev_enr = enroll(self.ev, self.course)
        complete(self.ev, self.quiz, quiz_score=0.0, quiz_answers=[False, False],
                 engagement_data={'quiz_selected': [1, 0]})
        add_event(self.ev, self.quiz, 'quiz_answer', question_index=0, selected=1, seconds_on_question=30)

        self.old = make_user('old')
        self.old_enr = enroll(self.old, self.course)
        complete(self.old, self.text)
