from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment, LearningPillar, Lesson, LessonProgress, LessonSession
from hub.serializers import (
    ContinueLearningSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    LessonSerializer,
    ModuleLearnSerializer,
    MyLearningEnrollmentSerializer,
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

        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            from hub.models.recommendations import CourseView
            CourseView.objects.create(user=request.user, course=course)

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

        if created:
            from hub.models.recommendations import (
                CourseRecommendation,
                RecommendationConfig,
                RecommendationEvent,
            )
            rec = CourseRecommendation.objects.filter(
                user=request.user, course=course,
            ).first()
            if rec:
                config = RecommendationConfig.get()
                RecommendationEvent.objects.create(
                    user=request.user,
                    course=course,
                    event_type=RecommendationEvent.EventType.ENROLLED,
                    rank=0,
                    source=rec.source,
                    weights_snapshot={
                        'alpha':         config.alpha,
                        'beta':          config.beta,
                        'gamma':         config.gamma,
                        'bandit_active': config.bandit_active,
                    },
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

        LessonSession.objects.create(user=request.user, lesson=lesson)

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
            enrollment = Enrollment.objects.select_related('course').get(
                user=request.user, course_id=pk,
            )
        except Enrollment.DoesNotExist:
            # Distinguish "course not found" from "not enrolled"
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        course = enrollment.course

        try:
            lesson = Lesson.objects.select_related('module').get(
                pk=lesson_pk, module__course=course,
            )
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        lp, created = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        if created:
            now = timezone.now()
            lp.completed_at = now

            session = LessonSession.objects.filter(
                user=request.user, lesson=lesson,
            ).order_by('-started_at').first()
            if session:
                lp.time_spent_seconds = max(0, int((now - session.started_at).total_seconds()))

            quiz_answers_raw = request.data.get('quiz_answers', [])
            if lesson.lesson_type == 'quiz' and quiz_answers_raw and lesson.quiz_data:
                booleans = []
                for i, selected in enumerate(quiz_answers_raw):
                    if i < len(lesson.quiz_data):
                        options = lesson.quiz_data[i].get('options', [])
                        if isinstance(selected, int) and 0 <= selected < len(options):
                            booleans.append(bool(options[selected].get('is_correct', False)))
                        else:
                            booleans.append(False)
                # Pad to full question count so score denominator is always len(quiz_data)
                while len(booleans) < len(lesson.quiz_data):
                    booleans.append(False)
                lp.quiz_answers = booleans
                lp.quiz_score = sum(booleans) / len(booleans) if booleans else 0.0

            engagement = dict(request.data.get('engagement_data') or {})
            if lesson.lesson_type == 'assignment' and 'submission' in engagement:
                engagement['word_count'] = len(str(engagement['submission']).split())
            lp.engagement_data = engagement

            lp.save()

        total = Lesson.objects.filter(module__course=course, is_required=True).count()
        completed_count = LessonProgress.objects.filter(
            user=request.user,
            lesson__module__course=course,
            lesson__is_required=True,
        ).count()
        progress_pct = round((completed_count / total) * 100) if total > 0 else 0

        just_completed = progress_pct == 100 and enrollment.completed_at is None
        enrollment.progress_pct = progress_pct
        enrollment.current_module = lesson.module
        if just_completed:
            enrollment.completed_at = timezone.now()
        enrollment.save()

        if just_completed and hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.competency_score < 6:
                profile.competency_score = min(profile.competency_score + 1, 6)
                profile.save(update_fields=['competency_score'])
                from hub.tasks import compute_user_recommendations
                compute_user_recommendations.delay(request.user.id)

        return Response({
            'lesson_id': lesson.id,
            'is_completed': True,
            'progress_pct': progress_pct,
        })


class MyLearningView(APIView):
    """GET /api/my-learning/ — User's enrollments split into in-progress and completed."""

    def get(self, request):
        enrollments = list(
            Enrollment.objects
            .filter(user=request.user)
            .select_related('course__pillar', 'current_module')
            .prefetch_related('course__modules')
        )

        in_progress = [e for e in enrollments if e.progress_pct < 100]
        completed = [e for e in enrollments if e.progress_pct == 100]
        continue_learning = in_progress[0] if in_progress else None

        return Response({
            'continue_learning': (
                MyLearningEnrollmentSerializer(continue_learning).data
                if continue_learning else None
            ),
            'in_progress': MyLearningEnrollmentSerializer(in_progress, many=True).data,
            'completed': MyLearningEnrollmentSerializer(completed, many=True).data,
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
