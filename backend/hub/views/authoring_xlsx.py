from io import BytesIO

from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, CourseEditHistory, Lesson, Module
from hub.serializers import CourseAuthoringSerializer
from hub.xlsx_transfer import MAX_IMPORT_BYTES, build_course_workbook, parse_course_workbook

from .permissions import IsContentCreator

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class AuthoringCourseExportView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        try:
            course = Course.objects.select_related('pillar').prefetch_related(
                'modules__lessons',
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
                is_published=False,
                created_by=request.user,
            )
            if payload.get('subjects'):
                course.subjects.set(payload['subjects'])
            for module_data in payload['modules']:
                module = Module.objects.create(
                    course=course,
                    title=module_data['title'],
                    description=module_data['description'],
                    order=module_data['order'],
                    duration_minutes=module_data['duration_minutes'],
                )
                for lesson_data in sorted(module_data['lessons'].values(), key=lambda lesson: lesson['order']):
                    Lesson.objects.create(module=module, **{
                        k: lesson_data[k] for k in (
                            'title', 'description', 'lesson_type', 'content',
                            'duration_minutes', 'order', 'is_required', 'quiz_data',
                        )
                    })
            CourseEditHistory.objects.create(
                course=course,
                editor=request.user,
                changes={'course_imported': {'title': course.title}},
            )

        return Response(CourseAuthoringSerializer(course).data, status=status.HTTP_201_CREATED)
