from django.db.models import Sum
from rest_framework import serializers

from hub.models import Course, Enrollment, Lesson


class CourseAnalyticsSerializer(serializers.ModelSerializer):
    enrolled = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()
    in_progress = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    avg_time_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'enrolled', 'completed', 'in_progress', 'completion_rate', 'avg_time_minutes']

    def _enrollments(self, obj):
        cache = self.context.setdefault('_enrollment_cache', {})
        if obj.id not in cache:
            cache[obj.id] = list(Enrollment.objects.filter(course=obj))
        return cache[obj.id]

    def get_enrolled(self, obj):
        return len(self._enrollments(obj))

    def get_completed(self, obj):
        return sum(1 for e in self._enrollments(obj) if e.progress_pct == 100)

    def get_in_progress(self, obj):
        return sum(1 for e in self._enrollments(obj) if 0 < e.progress_pct < 100)

    def get_completion_rate(self, obj):
        enrollments = self._enrollments(obj)
        if not enrollments:
            return 0
        completed = sum(1 for e in enrollments if e.progress_pct == 100)
        return round(completed / len(enrollments) * 100)

    def get_avg_time_minutes(self, obj):
        result = Lesson.objects.filter(module__course=obj).aggregate(total=Sum('duration_minutes'))
        return result['total'] or 0
