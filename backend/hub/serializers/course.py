from django.db.models import Avg
from rest_framework import serializers

from hub.models import Course, CourseEditHistory, Enrollment, LearningPillar

from .content import ModuleSerializer


class PillarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPillar
        fields = ['id', 'name', 'slug']


class CourseListSerializer(serializers.ModelSerializer):
    pillar = PillarSerializer(read_only=True)
    module_count = serializers.IntegerField(source='modules.count', read_only=True)
    progress_pct = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'pillar',
            'level', 'duration_hours', 'module_count',
            'progress_pct', 'is_enrolled',
        ]

    def _enrollment(self, obj):
        user = self.context['request'].user
        cache = self.context.setdefault('_enrollment_cache', {})
        if obj.id not in cache:
            try:
                cache[obj.id] = Enrollment.objects.get(user=user, course=obj)
            except Enrollment.DoesNotExist:
                cache[obj.id] = None
        return cache[obj.id]

    def get_progress_pct(self, obj):
        enrollment = self._enrollment(obj)
        return enrollment.progress_pct if enrollment else None

    def get_is_enrolled(self, obj):
        return self._enrollment(obj) is not None


class CourseDetailSerializer(serializers.ModelSerializer):
    pillar = PillarSerializer(read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)
    module_count = serializers.IntegerField(source='modules.count', read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()
    current_module_id = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'pillar', 'level', 'duration_hours',
            'learning_outcomes', 'module_count', 'modules',
            'is_enrolled', 'progress_pct', 'current_module_id',
        ]

    def _enrollment(self, obj):
        user = self.context['request'].user
        try:
            return Enrollment.objects.get(user=user, course=obj)
        except Enrollment.DoesNotExist:
            return None

    def get_is_enrolled(self, obj):
        return self._enrollment(obj) is not None

    def get_progress_pct(self, obj):
        e = self._enrollment(obj)
        return e.progress_pct if e else None

    def get_current_module_id(self, obj):
        e = self._enrollment(obj)
        return e.current_module_id if e else None


class ContinueLearningSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source='course.id')
    course_title = serializers.CharField(source='course.title')
    current_module_title = serializers.CharField(source='current_module.title', default=None)

    class Meta:
        model = Enrollment
        fields = ['course_id', 'course_title', 'current_module_title', 'progress_pct']


class PillarSummarySerializer(serializers.ModelSerializer):
    course_count = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = LearningPillar
        fields = ['id', 'name', 'slug', 'description', 'course_count', 'progress_pct']

    def get_course_count(self, obj):
        return obj.courses.count()

    def get_progress_pct(self, obj):
        user = self.context['request'].user
        enrollments = Enrollment.objects.filter(user=user, course__pillar=obj)
        if not enrollments.exists():
            return 0
        return round(enrollments.aggregate(avg=Avg('progress_pct'))['avg'] or 0)


class CourseAuthoringSerializer(serializers.ModelSerializer):
    pillar = PillarSerializer(read_only=True)
    pillar_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningPillar.objects.all(), source='pillar', write_only=True,
    )
    modules = ModuleSerializer(many=True, read_only=True)
    module_count = serializers.IntegerField(source='modules.count', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'pillar', 'pillar_id', 'level',
            'duration_hours', 'learning_outcomes', 'is_published', 'module_count', 'modules',
        ]
        read_only_fields = ['is_published']


class CourseEditHistorySerializer(serializers.ModelSerializer):
    editor_username = serializers.CharField(source='editor.username', default='(deleted user)')

    class Meta:
        model = CourseEditHistory
        fields = ['id', 'editor_username', 'edited_at', 'changes']
