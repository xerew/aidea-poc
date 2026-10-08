"""Reuse an existing module: browse modules from other courses and copy one
(with its activities and resources) into the course being edited."""
import copy

from django.db import transaction
from django.db.models import Count, Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Activity, Course, CourseEditHistory, Module
from hub.serializers import ModuleAuthoringSerializer
from hub.translation_sync import _target_langs, resync_lesson, resync_module

from .permissions import IsContentCreator, can_edit_course


def _can_reuse(user, course):
    """A module can be copied from a published course, or from any course the
    user may edit (their own drafts, co-edited courses; admins: all)."""
    return course.is_published or can_edit_course(user, course)


def _clone(obj, **overrides):
    """New row with every concrete field of `obj` copied (JSON deep-copied),
    except the primary key and anything in `overrides` (keyed by attname)."""
    data = {
        f.attname: copy.deepcopy(getattr(obj, f.attname))
        for f in obj._meta.concrete_fields
        if not f.primary_key and f.attname not in overrides
    }
    data.update(overrides)
    return type(obj).objects.create(**data)


def copy_module(source, target_course, order):
    """Deep-copy a module into `target_course` at `order`. Links to learning
    outcomes are dropped: they index the source course's outcomes."""
    new_module = _clone(source, course_id=target_course.id, order=order, related_outcomes=[])
    for activity in source.lessons.order_by('order').prefetch_related('resources'):
        new_activity = _clone(activity, module_id=new_module.id)
        for resource in activity.resources.order_by('order'):
            new_resource = _clone(resource, activity_id=new_activity.id)
            # Copies share the unpacked folders, which are never deleted.
            for package in resource.h5p_packages.all():
                _clone(package, resource_id=new_resource.id, file=package.file.name)
    return new_module


class ModuleLibraryView(APIView):
    """GET /authoring/module-library/?exclude_course=<id> — modules the user may
    reuse, grouped by course on the client."""
    permission_classes = [IsContentCreator]

    def get(self, request):
        exclude = request.query_params.get('exclude_course')
        courses = (
            Course.objects.select_related('pillar')
            .prefetch_related('collaborators')
            .order_by('title')
        )
        if exclude and exclude.isdigit():
            courses = courses.exclude(pk=int(exclude))
        allowed = {c.id: c for c in courses if _can_reuse(request.user, c)}
        modules = (
            Module.objects.filter(course_id__in=allowed)
            .annotate(activity_count=Count('lessons'))
            .order_by('course__title', 'order')
        )
        return Response([
            {
                'id': m.id,
                'title': m.title,
                'description': m.description,
                'duration_minutes': m.duration_minutes,
                'activity_count': m.activity_count,
                'course_id': m.course_id,
                'course_title': allowed[m.course_id].title,
                'course_published': allowed[m.course_id].is_published,
            }
            for m in modules
        ])


class ModuleImportView(APIView):
    """POST /authoring/courses/<pk>/modules/import/ {module_id} — append a copy
    of an existing module (activities and resources included) to the course."""
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        course = Course.objects.filter(pk=pk).first()
        if not course:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, course):
            return Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)

        source = (
            Module.objects.select_related('course')
            .filter(pk=request.data.get('module_id'))
            .first()
            if str(request.data.get('module_id', '')).isdigit() else None
        )
        if not source or not _can_reuse(request.user, source.course):
            return Response({'detail': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            order = (Module.objects.filter(course=course).aggregate(Max('order'))['order__max'] or 0) + 1
            module = copy_module(source, course, order)
            CourseEditHistory.objects.create(
                course=course, editor=request.user,
                changes={'module_imported': {
                    'title': module.title, 'from_course': source.course.title, 'order': order,
                }},
            )

        # Translate into this course's languages the copy doesn't already cover.
        missing = [lang for lang in _target_langs(course) if lang not in (source.translations or {})]
        if missing:
            resync_module(module)
            for activity in Activity.objects.filter(module=module):
                resync_lesson(activity)

        return Response(ModuleAuthoringSerializer(module).data, status=status.HTTP_201_CREATED)

