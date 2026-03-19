from django.db.models import Avg
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import UserProfile, LearningPillar, Course, Module, Enrollment


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['user_type', 'avatar_initials']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class AideaTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'order']


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'pillar', 'modules']


class ContinueLearningSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title')
    current_module_title = serializers.CharField(source='current_module.title', default=None)

    class Meta:
        model = Enrollment
        fields = ['course_title', 'current_module_title', 'progress_pct']


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
        enrollments = Enrollment.objects.filter(
            user=user,
            course__pillar=obj,
        )
        if not enrollments.exists():
            return 0
        return round(enrollments.aggregate(avg=Avg('progress_pct'))['avg'] or 0)
