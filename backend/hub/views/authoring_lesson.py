from django.db.models import Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import CourseEditHistory, Lesson, Module
from hub.serializers import LessonSerializer
from hub.translation import LANGUAGE_NAMES

from .permissions import IsContentCreator, can_edit_published

TRANSLATABLE_LESSON_FIELDS = ['title', 'description', 'content', 'quiz_data']


class AuthoringLessonView(APIView):
    """POST — create a new lesson inside a module."""
    permission_classes = [IsContentCreator]

    def post(self, request, pk, module_pk):
        try:
            module = Module.objects.select_related('course').get(pk=module_pk, course_id=pk)
        except Module.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.is_published and not can_edit_published(request.user, module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
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
        if lesson.module.course.is_published and not can_edit_published(request.user, lesson.module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        lang = request.query_params.get('lang')
        if lang:
            source_language = lesson.module.course.source_language
            if lang not in LANGUAGE_NAMES or lang == source_language:
                return Response(
                    {'detail': 'Invalid or source language.'}, status=status.HTTP_400_BAD_REQUEST,
                )
            blob = dict(lesson.translations.get(lang, {}))
            for field in TRANSLATABLE_LESSON_FIELDS:
                if field in request.data:
                    blob[field] = request.data[field]
            lesson.translations[lang] = blob
            lesson.save(update_fields=['translations'])
            return Response(LessonSerializer(lesson).data)

        serializer = LessonSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changes = {}
        for field in ['title', 'description', 'content', 'quiz_data', 'lesson_type', 'duration_minutes', 'is_required']:
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
        if lesson.module.course.is_published and not can_edit_published(request.user, lesson.module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        CourseEditHistory.objects.create(
            course=lesson.module.course,
            editor=request.user,
            changes={'lesson_deleted': {'lesson_title': lesson.title, 'module_title': lesson.module.title}},
        )
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthoringLessonReorderView(APIView):
    """PATCH — reorder lessons within a module. Body: {"order": [id, id, ...]}"""
    permission_classes = [IsContentCreator]

    def patch(self, request, pk, module_pk):
        try:
            module = Module.objects.select_related('course').get(pk=module_pk, course_id=pk)
        except Module.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.is_published and not can_edit_published(request.user, module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = request.data.get('order', [])
        if not isinstance(order, list) or not order:
            return Response(
                {'detail': '"order" must be a non-empty list of lesson IDs.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lessons = {lesson.pk: lesson for lesson in Lesson.objects.filter(module=module, pk__in=order)}
        if len(lessons) != len(order):
            return Response({'detail': 'Invalid lesson IDs.'}, status=status.HTTP_400_BAD_REQUEST)

        for position, lesson_id in enumerate(order, start=1):
            lesson = lessons[lesson_id]
            lesson.order = position
            lesson.save(update_fields=['order'])

        CourseEditHistory.objects.create(
            course=module.course,
            editor=request.user,
            changes={'lessons_reordered': {'module_title': module.title, 'order': order}},
        )
        return Response(LessonSerializer(Lesson.objects.filter(module=module), many=True).data)
