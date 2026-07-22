from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LessonProgress
from hub.views.permissions import IsContentCreator

from .serializers import CourseAnalyticsSerializer


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

        courses_data = CourseAnalyticsSerializer(courses, many=True, context={}).data

        return Response({'summary': summary, 'courses': courses_data})
