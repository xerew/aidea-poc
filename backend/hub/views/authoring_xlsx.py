from io import BytesIO

from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Activity, Course, CourseEditHistory, Module, Resource
from hub.serializers import CourseAuthoringSerializer
from hub.xlsx_transfer import MAX_IMPORT_BYTES, build_course_workbook, parse_course_workbook

from .permissions import IsContentCreator

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class AuthoringCourseExportView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        try:
            course = Course.objects.select_related('pillar').prefetch_related(
                'modules__lessons__resources', 'subjects', 'additional_pillars',
            ).get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        buffer = BytesIO()
        build_course_workbook(course).save(buffer)
        filename = f'{slugify(course.title) or "course"}.xlsx'
        response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class AuthoringCourseTemplateView(APIView):
    """GET — download a blank course workbook (headers + dropdowns, no data)."""
    permission_classes = [IsContentCreator]

    def get(self, request):
        buffer = BytesIO()
        build_course_workbook().save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
        response['Content-Disposition'] = 'attachment; filename="aidea-course-template.xlsx"'
        return response


def _create_activity(module, data):
    resources = [data['resources'][k] for k in sorted(data['resources'])]
    activity = Activity.objects.create(
        module=module,
        title=data['title'],
        description=data['description'],
        duration_minutes=data['duration_minutes'],
        order=data['order'],
        # Legacy column, kept meaningful for the rollback window.
        lesson_type=resources[0]['type'],
        translations=data.get('translations', {}),
    )
    for position, r in enumerate(resources, start=1):
        Resource.objects.create(activity=activity, order=position, **{
            k: r[k] for k in (
                'type', 'is_required', 'title', 'content', 'url', 'caption',
                'instructions', 'quiz_data', 'translations',
            )
        })


class AuthoringCourseImportView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'errors': ['No file provided.']}, status=status.HTTP_400_BAD_REQUEST)
        if not file.name.lower().endswith('.xlsx'):
            return Response({'errors': ['Only .xlsx files are supported.']}, status=status.HTTP_400_BAD_REQUEST)
        if file.size > MAX_IMPORT_BYTES:
            return Response({'errors': ['File too large (max 5 MB).']}, status=status.HTTP_400_BAD_REQUEST)

        payload, errors = parse_course_workbook(file)
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        title = payload['title']
        if Course.objects.filter(title=title).exists():
            candidate, n = f'{title} (imported)', 2
            while Course.objects.filter(title=candidate).exists():
                candidate = f'{title} (imported {n})'
                n += 1
            title = candidate

        with transaction.atomic():
            course = Course.objects.create(
                title=title,
                description=payload['description'],
                pillar=payload['pillar'],
                level=payload['level'],
                duration_hours=payload['duration_hours'],
                content_format=payload['content_format'],
                learning_outcomes=payload['learning_outcomes'],
                cross_axis_relevance=payload['cross_axis_relevance'],
                target_audience=payload['target_audience'],
                target_audience_other=payload['target_audience_other'],
                educational_levels=payload['educational_levels'],
                educational_level_other=payload['educational_level_other'],
                prior_knowledge=payload['prior_knowledge'],
                translations=payload.get('translations', {}),
                translation_status=payload.get('translation_status', {}),
                is_published=False,
                created_by=request.user,
            )
            if payload.get('subjects'):
                course.subjects.set(payload['subjects'])
            if payload.get('additional_pillars'):
                course.additional_pillars.set(payload['additional_pillars'])
            for module_data in payload['modules']:
                module = Module.objects.create(
                    course=course,
                    title=module_data['title'],
                    description=module_data['description'],
                    order=module_data['order'],
                    duration_minutes=module_data['duration_minutes'],
                    related_outcomes=module_data['related_outcomes'],
                    translations=module_data.get('translations', {}),
                )
                for activity_data in sorted(module_data['activities'].values(), key=lambda a: a['order']):
                    _create_activity(module, activity_data)
            CourseEditHistory.objects.create(
                course=course,
                editor=request.user,
                changes={'course_imported': {'title': course.title}},
            )

        return Response(CourseAuthoringSerializer(course).data, status=status.HTTP_201_CREATED)
