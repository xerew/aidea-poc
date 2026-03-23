from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LessonProgress
from hub.views.permissions import IsContentCreator

from .serializers import CourseAnalyticsSerializer


class AnalyticsOverviewView(APIView):
    """GET /api/analytics/overview/ — Content creator analytics dashboard."""

    permission_classes = [IsContentCreator]

    def get(self, request):
        courses = list(
            Course.objects
            .filter(created_by=request.user)
            .prefetch_related('modules__lessons')
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

        summary = {
            'total_enrollments': total_enrollments,
            'completion_rate': completion_rate,
            'quiz_attempts': quiz_attempts,
            'courses_created': len(courses),
        }

        courses_data = CourseAnalyticsSerializer(courses, many=True, context={}).data

        return Response({'summary': summary, 'courses': courses_data})
