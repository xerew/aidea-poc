from django.db.models import Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, CourseEditHistory, Module
from hub.serializers import ModuleSerializer, ModuleWithLessonsSerializer

from .permissions import IsContentCreator, can_edit_published


class AuthoringModuleView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if course.is_published and not can_edit_published(request.user, course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        if module.course.is_published and not can_edit_published(request.user, module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        if module.course.is_published and not can_edit_published(request.user, module.course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        CourseEditHistory.objects.create(
            course=module.course,
            editor=request.user,
            changes={'module_deleted': {'title': module.title, 'order': module.order}},
        )
        module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthoringModuleReorderView(APIView):
    """PATCH — reorder modules within a course. Body: {"order": [id, id, ...]}"""
    permission_classes = [IsContentCreator]

    def patch(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if course.is_published and not can_edit_published(request.user, course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = request.data.get('order', [])
        if not isinstance(order, list) or not order:
            return Response(
                {'detail': '"order" must be a non-empty list of module IDs.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        modules = {m.pk: m for m in Module.objects.filter(course=course, pk__in=order)}
        if len(modules) != len(order):
            return Response({'detail': 'Invalid module IDs.'}, status=status.HTTP_400_BAD_REQUEST)

        for position, module_id in enumerate(order, start=1):
            mod = modules[module_id]
            mod.order = position
            mod.save(update_fields=['order'])

        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'modules_reordered': {'order': order}},
        )
        return Response(ModuleSerializer(Module.objects.filter(course=course), many=True).data)


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
