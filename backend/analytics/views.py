from io import BytesIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, CourseCollaborator, Enrollment, ResourceProgress, UserProfile
from hub.views.permissions import IsContentCreator

from .learning import CourseData, content_tree, learner_rows, learner_timeline
from .serializers import CourseAnalyticsSerializer
from .workbook import build_learning_workbook

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def scoped_courses(user):
    """Which courses' analytics a user may see: admins and AIDEA partners see
    every course; content creators see the ones they authored or co-edit."""
    qs = Course.objects.select_related('created_by', 'pillar')
    if user.profile.user_type in (UserProfile.UserType.ADMIN, UserProfile.UserType.AIDEA_PARTNER):
        return qs
    return qs.filter(
        Q(created_by=user)
        | Q(collaborators__user=user, collaborators__role=CourseCollaborator.Role.CO_EDITOR),
    ).distinct()


def co_editor_course_ids(user):
    return set(
        CourseCollaborator.objects.filter(
            user=user, role=CourseCollaborator.Role.CO_EDITOR,
        ).values_list('course_id', flat=True)
    )


class AnalyticsOverviewView(APIView):
    """GET /api/analytics/overview/ — Content creator analytics dashboard."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        # Admins/partners see every course; content creators see only their own.
        courses = list(
            scoped_courses(request.user)
            .prefetch_related('modules__lessons')
            .order_by('title')
        )

        total_enrollments = Enrollment.objects.filter(course__in=courses).count()
        completed_enrollments = Enrollment.objects.filter(course__in=courses, progress_pct=100).count()
        completion_rate = (
            round(completed_enrollments / total_enrollments * 100) if total_enrollments else 0
        )
        quiz_attempts = ResourceProgress.objects.filter(
            resource__type='quiz',
            resource__activity__module__course__in=courses,
            completed_at__isnull=False,
        ).count()

        # "Courses Created" stays the count the viewer actually authored, even
        # though the breakdown below spans the whole published catalog.
        courses_created = sum(1 for c in courses if c.created_by_id == request.user.id)

        summary = {
            'total_enrollments': total_enrollments,
            'completion_rate': completion_rate,
            'quiz_attempts': quiz_attempts,
            'courses_created': courses_created,
        }

        courses_data = CourseAnalyticsSerializer(
            courses, many=True,
            context={'request': request, 'editable_course_ids': co_editor_course_ids(request.user)},
        ).data

        return Response({'summary': summary, 'courses': courses_data})


def _xlsx_response(workbook, name):
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response


class AnalyticsExportView(APIView):
    """GET — the learning analytics workbook for every course in scope (or ?ids=)."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        courses = scoped_courses(request.user).order_by('title')
        # Optional subset selected in the export dialog: ?ids=1,2,3
        ids_param = request.query_params.get('ids')
        if ids_param:
            wanted = {int(x) for x in ids_param.split(',') if x.strip().isdigit()}
            courses = courses.filter(id__in=wanted)
        name = f'{slugify(request.user.username) or "analytics"}-analytics.xlsx'
        return _xlsx_response(build_learning_workbook(courses), name)


class _CourseAnalyticsView(APIView):
    """Base for one course's analytics: 404 outside the viewer's scope."""

    permission_classes = [IsContentCreator]

    def course_or_none(self, request, pk):
        return scoped_courses(request.user).filter(pk=pk).first()


def _not_found():
    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


class CourseContentView(_CourseAnalyticsView):
    """GET — module → activity → resource tree with reached / done / typical
    time / dropped-here and notes per resource type."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        return Response(content_tree(CourseData(course)))


class CourseLearnersView(_CourseAnalyticsView):
    """GET — one row per enrolled learner with time, position and status."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        return Response({
            'course': {'id': course.id, 'title': course.title},
            'learners': learner_rows(CourseData(course)),
        })


class CourseLearnerTimelineView(_CourseAnalyticsView):
    """GET — one learner's timeline through the course."""

    def get(self, request, pk, user_id):
        course = self.course_or_none(request, pk)
        timeline = learner_timeline(CourseData(course), user_id) if course else None
        if timeline is None:
            return _not_found()
        return Response(timeline)


class CourseExportView(_CourseAnalyticsView):
    """GET — the learning analytics workbook for one course."""

    def get(self, request, pk):
        course = self.course_or_none(request, pk)
        if course is None:
            return _not_found()
        name = f'{slugify(course.title) or "course"}-analytics.xlsx'
        return _xlsx_response(build_learning_workbook([course]), name)
