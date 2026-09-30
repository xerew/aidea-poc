from django.db.models import Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Activity, CourseEditHistory, Resource
from hub.serializers import ResourceSerializer
from hub.translation import LANGUAGE_NAMES

from .permissions import IsContentCreator, can_edit_course, can_translate_course

TRANSLATABLE_RESOURCE_FIELDS = ['title', 'content', 'caption', 'instructions', 'quiz_data']


def _get_activity(course_pk, module_pk, lesson_pk):
    return (
        Activity.objects.select_related('module__course')
        .filter(pk=lesson_pk, module_id=module_pk, module__course_id=course_pk)
        .first()
    )


class AuthoringResourceView(APIView):
    """POST — add a resource to an activity."""
    permission_classes = [IsContentCreator]

    def post(self, request, pk, module_pk, lesson_pk):
        activity = _get_activity(pk, module_pk, lesson_pk)
        if not activity:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, activity.module.course):
            return Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ResourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_order = (
            Resource.objects.filter(activity=activity).aggregate(Max('order'))['order__max'] or 0
        ) + 1
        resource = serializer.save(activity=activity, order=next_order)
        CourseEditHistory.objects.create(
            course=activity.module.course, editor=request.user,
            changes={'resource_added': {'activity': activity.title, 'type': resource.type}},
        )
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)


class AuthoringResourceDetailView(APIView):
    """PATCH (source or ?lang= translation) / DELETE a resource."""
    permission_classes = [IsContentCreator]

    def _get(self, pk, module_pk, lesson_pk, resource_pk):
        return (
            Resource.objects.select_related('activity__module__course')
            .filter(
                pk=resource_pk, activity_id=lesson_pk,
                activity__module_id=module_pk, activity__module__course_id=pk,
            )
            .first()
        )

    def patch(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = self._get(pk, module_pk, lesson_pk, resource_pk)
        if not resource:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        course = resource.activity.module.course

        lang = request.query_params.get('lang')
        allowed = (
            can_translate_course(request.user, course) if lang
            else can_edit_course(request.user, course)
        )
        if not allowed:
            return Response({'detail': 'You cannot edit this resource.'}, status=status.HTTP_403_FORBIDDEN)

        if lang:
            if lang not in LANGUAGE_NAMES or lang == course.source_language:
                return Response({'detail': 'Invalid or source language.'}, status=status.HTTP_400_BAD_REQUEST)
            if 'quiz_data' in request.data:
                translated = request.data['quiz_data']
                try:
                    ResourceSerializer().validate_quiz_data(translated)
                except Exception as exc:  # noqa: BLE001 - surface DRF validation detail
                    return Response({'quiz_data': getattr(exc, 'detail', str(exc))},
                                    status=status.HTTP_400_BAD_REQUEST)
            blob = dict(resource.translations.get(lang, {}))
            for field in TRANSLATABLE_RESOURCE_FIELDS:
                if field in request.data:
                    blob[field] = request.data[field]
            resource.translations[lang] = blob
            resource.save(update_fields=['translations'])
            return Response(ResourceSerializer(resource).data)

        serializer = ResourceSerializer(resource, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ResourceSerializer(resource).data)

    def delete(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = self._get(pk, module_pk, lesson_pk, resource_pk)
        if not resource:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, resource.activity.module.course):
            return Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthoringResourceReorderView(APIView):
    """PATCH — reorder resources within an activity. Body: {"order": [id, ...]}"""
    permission_classes = [IsContentCreator]

    def patch(self, request, pk, module_pk, lesson_pk):
        activity = _get_activity(pk, module_pk, lesson_pk)
        if not activity:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, activity.module.course):
            return Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)

        order = request.data.get('order', [])
        if not isinstance(order, list) or not order:
            return Response({'detail': '"order" must be a non-empty list of resource IDs.'},
                            status=status.HTTP_400_BAD_REQUEST)
        resources = {r.pk: r for r in Resource.objects.filter(activity=activity, pk__in=order)}
        if len(resources) != len(order):
            return Response({'detail': 'Invalid resource IDs.'}, status=status.HTTP_400_BAD_REQUEST)
        for position, rid in enumerate(order, start=1):
            r = resources[rid]
            r.order = position
            r.save(update_fields=['order'])
        return Response(ResourceSerializer(Resource.objects.filter(activity=activity), many=True).data)
