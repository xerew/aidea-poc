from io import BytesIO

from django.db.models import Q
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LessonProgress
from hub.views.permissions import IsContentCreator

from .reports import build_analytics_workbook, build_course_teacher_report
from .serializers import CourseAnalyticsSerializer

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class AnalyticsOverviewView(APIView):
    """GET /api/analytics/overview/ — Content creator analytics dashboard."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        # #11: creators see engagement across every published course (real
        # platform usage), plus their own unpublished drafts — otherwise a
        # creator who has authored nothing sees an empty dashboard while the
        # catalog's enrolled teachers stay invisible.
        courses = list(
            Course.objects
            .filter(Q(is_published=True) | Q(created_by=request.user))
            .prefetch_related('modules__lessons')
            .distinct()
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
            course = Course.objects.get(pk=pk, created_by=request.user)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_course_teacher_report(course))


class AnalyticsExportView(APIView):
    """GET — #26: xlsx workbook, one sheet per authored course, one row per
    enrolled teacher."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        courses = (
            Course.objects
            .filter(created_by=request.user)
            .prefetch_related('modules__lessons')
            .order_by('title')
        )
        buffer = BytesIO()
        build_analytics_workbook(courses).save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
        name = f'{slugify(request.user.username) or "analytics"}-analytics.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{name}"'
        return response
