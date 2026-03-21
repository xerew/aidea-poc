from django.db.models import Max
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Course,
    CourseEditHistory,
    Enrollment,
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)
from .serializers import (
    AideaTokenObtainPairSerializer,
    ContinueLearningSerializer,
    CourseAuthoringSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    LessonSerializer,
    ModuleSerializer,
    ModuleWithLessonsSerializer,
    PillarSerializer,
    PillarSummarySerializer,
)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AideaTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out.'})


class CoursesView(APIView):
    def get(self, request):
        qs = Course.objects.select_related('pillar').prefetch_related('modules').filter(is_published=True)
        pillar = request.query_params.get('pillar')
        level  = request.query_params.get('level')
        search = request.query_params.get('search')
        if pillar:
            qs = qs.filter(pillar__slug=pillar)
        if level:
            qs = qs.filter(level=level)
        if search:
            qs = qs.filter(title__icontains=search)
        serializer = CourseListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class CourseDetailView(APIView):
    def get(self, request, pk):
        try:
            course = Course.objects.prefetch_related('modules').select_related('pillar').get(
                pk=pk, is_published=True,
            )
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseDetailSerializer(course, context={'request': request})
        return Response(serializer.data)


class CourseEnrollView(APIView):
    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk, is_published=True)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )
        return Response(
            {'enrolled': True, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class HomeView(APIView):
    def get(self, request):
        # Most recently accessed enrollment for "Continue Learning"
        latest_enrollment = (
            Enrollment.objects
            .filter(user=request.user)
            .select_related('course', 'current_module')
            .first()
        )

        continue_learning = (
            ContinueLearningSerializer(latest_enrollment).data
            if latest_enrollment else None
        )

        pillars = LearningPillar.objects.all()
        pillars_data = PillarSummarySerializer(
            pillars, many=True, context={'request': request}
        ).data

        return Response({
            'continue_learning': continue_learning,
            'pillars': pillars_data,
        })


# ── Authoring ────────────────────────────────────────────────────────────────

class IsContentCreator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR
        )


class AuthoringPillarsView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request):
        return Response(PillarSerializer(LearningPillar.objects.all(), many=True).data)


class AuthoringCoursesView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request):
        qs = (
            Course.objects
            .select_related('pillar')
            .prefetch_related('modules')
            .order_by('pillar__order', 'title')
        )
        return Response(CourseAuthoringSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CourseAuthoringSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'course_created': {'title': course.title}},
        )
        return Response(CourseAuthoringSerializer(course).data, status=status.HTTP_201_CREATED)


class AuthoringCourseDetailView(APIView):
    permission_classes = [IsContentCreator]

    def _get_course(self, pk):
        try:
            return Course.objects.prefetch_related('modules').select_related('pillar').get(pk=pk)
        except Course.DoesNotExist:
            return None

    def get(self, request, pk):
        course = self._get_course(pk)
        if not course:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CourseAuthoringSerializer(course).data)

    def patch(self, request, pk):
        course = self._get_course(pk)
        if not course:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published:
            return Response({'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CourseAuthoringSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changes = {}
        for field in ['title', 'description', 'level', 'duration_hours', 'learning_outcomes']:
            if field in serializer.validated_data:
                old_val = getattr(course, field)
                new_val = serializer.validated_data[field]
                if old_val != new_val:
                    changes[field] = {'old': old_val, 'new': new_val}
        if 'pillar' in serializer.validated_data:
            new_pillar = serializer.validated_data['pillar']
            if course.pillar_id != new_pillar.id:
                changes['pillar'] = {'old': course.pillar.name, 'new': new_pillar.name}

        serializer.save()

        if changes:
            CourseEditHistory.objects.create(course=course, editor=request.user, changes=changes)

        course.refresh_from_db()
        return Response(CourseAuthoringSerializer(course).data)


class AuthoringModuleView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if course.is_published:
            return Response({'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_order = (
            Module.objects.filter(course=course).aggregate(Max('order'))['order__max'] or 0
        ) + 1
        module = serializer.save(course=course, order=next_order)

        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'module_added': {'title': module.title, 'order': module.order}},
        )
        return Response(ModuleSerializer(module).data, status=status.HTTP_201_CREATED)


class AuthoringModuleDetailView(APIView):
    permission_classes = [IsContentCreator]

    def _get_module(self, course_pk, module_pk):
        try:
            return Module.objects.select_related('course').get(pk=module_pk, course_id=course_pk)
        except Module.DoesNotExist:
            return None

    def patch(self, request, pk, module_pk):
        module = self._get_module(pk, module_pk)
        if not module:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if module.course.is_published:
            return Response({'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ModuleSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changes = {}
        for field in ['title', 'description', 'duration_minutes']:
            if field in serializer.validated_data:
                old_val = getattr(module, field)
                new_val = serializer.validated_data[field]
                if old_val != new_val:
                    changes[field] = {'old': old_val, 'new': new_val}

        serializer.save()

        if changes:
            CourseEditHistory.objects.create(
                course=module.course,
                editor=request.user,
                changes={'module_edited': {'module_title': module.title, 'fields': changes}},
            )
        return Response(ModuleSerializer(module).data)

    def delete(self, request, pk, module_pk):
        module = self._get_module(pk, module_pk)
        if not module:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if module.course.is_published:
            return Response({'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

        CourseEditHistory.objects.create(
            course=module.course,
            editor=request.user,
            changes={'module_deleted': {'title': module.title, 'order': module.order}},
        )
        module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthoringCoursePublishView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published:
            return Response({'detail': 'Course is already published.'}, status=status.HTTP_400_BAD_REQUEST)

        course.is_published = True
        course.save()
        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'course_published': {'title': course.title}},
        )
        return Response(CourseAuthoringSerializer(course).data)


class AuthoringModuleEditorView(APIView):
    """GET a single module with its lessons for the module editor."""
    permission_classes = [IsContentCreator]

    def _get_module(self, course_pk, module_pk):
        try:
            return Module.objects.prefetch_related('lessons').select_related('course').get(
                pk=module_pk, course_id=course_pk,
            )
        except Module.DoesNotExist:
            return None

    def get(self, request, pk, module_pk):
        module = self._get_module(pk, module_pk)
        if not module:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ModuleWithLessonsSerializer(module).data)


class AuthoringLessonView(APIView):
    """POST — create a new lesson inside a module."""
    permission_classes = [IsContentCreator]

    def post(self, request, pk, module_pk):
        try:
            module = Module.objects.select_related('course').get(pk=module_pk, course_id=pk)
        except Module.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.is_published:
            return Response(
                {'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_order = (
            Lesson.objects.filter(module=module).aggregate(Max('order'))['order__max'] or 0
        ) + 1
        lesson = serializer.save(module=module, order=next_order)

        CourseEditHistory.objects.create(
            course=module.course,
            editor=request.user,
            changes={'lesson_added': {'module_title': module.title, 'lesson_title': lesson.title}},
        )
        return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)


class AuthoringLessonDetailView(APIView):
    """PATCH / DELETE a specific lesson."""
    permission_classes = [IsContentCreator]

    def _get_lesson(self, course_pk, module_pk, lesson_pk):
        try:
            return Lesson.objects.select_related('module__course').get(
                pk=lesson_pk, module_id=module_pk, module__course_id=course_pk,
            )
        except Lesson.DoesNotExist:
            return None

    def patch(self, request, pk, module_pk, lesson_pk):
        lesson = self._get_lesson(pk, module_pk, lesson_pk)
        if not lesson:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if lesson.module.course.is_published:
            return Response(
                {'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changes = {}
        for field in ['title', 'description', 'content', 'lesson_type', 'duration_minutes', 'is_required']:
            if field in serializer.validated_data:
                old_val = getattr(lesson, field)
                new_val = serializer.validated_data[field]
                if old_val != new_val:
                    changes[field] = {'old': old_val, 'new': new_val}

        serializer.save()

        if changes:
            CourseEditHistory.objects.create(
                course=lesson.module.course,
                editor=request.user,
                changes={'lesson_edited': {'lesson_title': lesson.title, 'fields': changes}},
            )
        return Response(LessonSerializer(lesson).data)

    def delete(self, request, pk, module_pk, lesson_pk):
        lesson = self._get_lesson(pk, module_pk, lesson_pk)
        if not lesson:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if lesson.module.course.is_published:
            return Response(
                {'detail': 'Published courses cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        CourseEditHistory.objects.create(
            course=lesson.module.course,
            editor=request.user,
            changes={'lesson_deleted': {'lesson_title': lesson.title, 'module_title': lesson.module.title}},
        )
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
