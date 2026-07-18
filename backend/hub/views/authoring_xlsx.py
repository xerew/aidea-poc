from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course
from hub.xlsx_transfer import build_course_workbook

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
