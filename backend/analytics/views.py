from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LessonProgress, UserProfile
from hub.views.permissions import IsContentCreator

from .reports import build_analytics_workbook, build_course_teacher_report
from .serializers import CourseAnalyticsSerializer

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def scoped_courses(user):
    """Which courses' analytics a user may see: admins and AIDEA partners see
    every course; content creators see only the ones they authored."""
    qs = Course.objects.select_related('created_by', 'pillar')
    if user.profile.user_type in (UserProfile.UserType.ADMIN, UserProfile.UserType.AIDEA_PARTNER):
        return qs
    return qs.filter(created_by=user)


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
        quiz_attempts = LessonProgress.objects.filter(
            lesson__lesson_type='quiz',
            lesson__module__course__in=courses,
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
            courses, many=True, context={'request': request},
        ).data

        return Response({'summary': summary, 'courses': courses_data})


class AnalyticsCourseTeachersView(APIView):
    """GET — #27: per-teacher detail (progress, time spent, quiz answers) for
    a course the requesting creator authored."""

    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        try:
            course = scoped_courses(request.user).get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_course_teacher_report(course))


class AnalyticsExportView(APIView):
    """GET — #26: xlsx workbook, one sheet per authored course, one row per
    enrolled teacher."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        courses = scoped_courses(request.user).prefetch_related('modules__lessons').order_by('title')
        # Optional subset selected in the export dialog: ?ids=1,2,3
        ids_param = request.query_params.get('ids')
        if ids_param:
            wanted = {int(x) for x in ids_param.split(',') if x.strip().isdigit()}
            courses = courses.filter(id__in=wanted)
        buffer = BytesIO()
        build_analytics_workbook(courses).save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
        name = f'{slugify(request.user.username) or "analytics"}-analytics.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{name}"'
        return response
