from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LearningPillar, Lesson, LessonProgress
from hub.serializers import (
    ContinueLearningSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    LessonSerializer,
    ModuleLearnSerializer,
    PillarSummarySerializer,
)


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


class CourseLearnView(APIView):
    """GET /courses/<pk>/learn/ — Course structure with per-user lesson completion for sidebar."""

    def get(self, request, pk):
        try:
            course = Course.objects.prefetch_related('modules__lessons').get(
                pk=pk, is_published=True,
            )
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        completed_ids = set(
            LessonProgress.objects.filter(
                user=request.user, lesson__module__course=course,
            ).values_list('lesson_id', flat=True)
        )

        modules_data = ModuleLearnSerializer(
            course.modules.all(),
            many=True,
            context={'completed_lesson_ids': completed_ids},
        ).data

        all_lessons = list(
            Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
        )
        first_incomplete_id = next(
            (lesson.id for lesson in all_lessons if lesson.id not in completed_ids),
            all_lessons[-1].id if all_lessons else None,
        )

        return Response({
            'id': course.id,
            'title': course.title,
            'progress_pct': enrollment.progress_pct,
            'modules': modules_data,
            'first_incomplete_lesson_id': first_incomplete_id,
        })


class LessonDetailView(APIView):
    """GET /courses/<pk>/lessons/<lesson_pk>/ — Full lesson with prev/next IDs."""

    def get(self, request, pk, lesson_pk):
        try:
            course = Course.objects.get(pk=pk, is_published=True)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            Enrollment.objects.get(user=request.user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        all_ids = list(
            Lesson.objects.filter(module__course=course)
            .order_by('module__order', 'order')
            .values_list('id', flat=True)
        )
        idx = all_ids.index(lesson.id)

        is_completed = LessonProgress.objects.filter(
            user=request.user, lesson=lesson,
        ).exists()

        return Response({
            **LessonSerializer(lesson).data,
            'module_id': lesson.module_id,
            'module_title': lesson.module.title,
            'is_completed': is_completed,
            'prev_lesson_id': all_ids[idx - 1] if idx > 0 else None,
            'next_lesson_id': all_ids[idx + 1] if idx < len(all_ids) - 1 else None,
        })


class LessonCompleteView(APIView):
    """POST /courses/<pk>/lessons/<lesson_pk>/complete/ — Mark lesson complete, recalculate progress."""

    def post(self, request, pk, lesson_pk):
        try:
            course = Course.objects.get(pk=pk, is_published=True)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        total = Lesson.objects.filter(module__course=course, is_required=True).count()
        completed = LessonProgress.objects.filter(
            user=request.user,
            lesson__module__course=course,
            lesson__is_required=True,
        ).count()
        progress_pct = round((completed / total) * 100) if total > 0 else 0

        enrollment.progress_pct = progress_pct
        enrollment.current_module = lesson.module
        enrollment.save()

        return Response({
            'lesson_id': lesson.id,
            'is_completed': True,
            'progress_pct': progress_pct,
        })


class HomeView(APIView):
    def get(self, request):
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
