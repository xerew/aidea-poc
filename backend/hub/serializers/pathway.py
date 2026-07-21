from rest_framework import serializers

from hub.models.content import Course
from hub.models.enrollment import Enrollment
from hub.models.pathway import LearningPathCourse, UserLearningPath
from hub.models.recommendations import CourseRecommendation

from .localize import localized, viewer_language


class PathwayCourseSerializer(serializers.ModelSerializer):
    pillar_name = serializers.CharField(source='pillar.name', read_only=True)
    status      = serializers.SerializerMethodField()
    order       = serializers.SerializerMethodField()
    title       = serializers.SerializerMethodField()

    class Meta:
        model  = Course
        fields = ['id', 'title', 'pillar_name', 'duration_hours', 'level', 'status', 'order']

    def get_title(self, obj):
        return localized(obj, 'title', viewer_language(self.context))

    def get_status(self, obj):
        user = self.context.get('user')
        if not user:
            return 'not_started'
        enrollment = Enrollment.objects.filter(user=user, course=obj).first()
        if not enrollment:
            return 'not_started'
        return 'completed' if enrollment.progress_pct == 100 else 'in_progress'

    def get_order(self, obj):
        path = self.context.get('path')
        if not path:
            return 0
        lpc = LearningPathCourse.objects.filter(path=path, course=obj).first()
        return lpc.order if lpc else 0


class UserLearningPathSerializer(serializers.ModelSerializer):
    path_name        = serializers.CharField(source='path.name', read_only=True)
    path_description = serializers.CharField(source='path.description', read_only=True)
    competency_level = serializers.SerializerMethodField()
    courses          = serializers.SerializerMethodField()
    progress         = serializers.SerializerMethodField()

    class Meta:
        model  = UserLearningPath
        fields = ['path_name', 'path_description', 'competency_level', 'courses', 'progress']

    def get_competency_level(self, obj):
        score = obj.user.profile.competency_score
        if score <= 2:
            return 'beginner'
        if score <= 4:
            return 'intermediate'
        return 'advanced'

    def get_courses(self, obj):
        courses = obj.path.courses.order_by('learningpathcourse__order')
        return PathwayCourseSerializer(
            courses, many=True, context={**self.context, 'path': obj.path},
        ).data

    def get_progress(self, obj):
        user       = obj.user
        course_ids = list(obj.path.courses.values_list('id', flat=True))
        total      = len(course_ids)
        completed  = Enrollment.objects.filter(
            user=user, course_id__in=course_ids, progress_pct=100,
        ).count()
        return {'completed': completed, 'total': total}


class RecommendationSerializer(serializers.ModelSerializer):
    course_id      = serializers.IntegerField(source='course.id')
    title          = serializers.SerializerMethodField()
    pillar_name    = serializers.CharField(source='course.pillar.name')
    level          = serializers.CharField(source='course.level')
    duration_hours = serializers.IntegerField(source='course.duration_hours')

    class Meta:
        model  = CourseRecommendation
        fields = ['course_id', 'title', 'pillar_name', 'level', 'duration_hours', 'score', 'reason', 'source']

    def get_title(self, obj):
        return localized(obj.course, 'title', viewer_language(self.context))
