import uuid
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub import h5p
from hub.models import CourseEditHistory, H5PPackage, Resource
from hub.serializers import ResourceSerializer
from hub.translation import LANGUAGE_NAMES
from hub.translation_sync import resync_resource

from .permissions import IsContentCreator, can_edit_course


def _error(code, detail):
    return Response({'code': code, 'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


class AuthoringH5PView(APIView):
    """POST (multipart: file, language) — upload or replace an H5P resource's
    package for one language ('' = main file). DELETE ?language= — remove it.
    Unpacked folders are kept on replace/remove (copies and past attempts)."""

    permission_classes = [IsContentCreator]

    def _resource(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = (
            Resource.objects.select_related('activity__module__course')
            .filter(
                pk=resource_pk, activity_id=lesson_pk,
                activity__module_id=module_pk, activity__module__course_id=pk,
            )
            .first()
        )
        if resource is None:
            return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, resource.activity.module.course):
            return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
        if resource.type != Resource.Type.H5P:
            return None, _error('not_h5p', 'This resource is not an H5P activity.')
        return resource, None

    def post(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        language = str(request.data.get('language') or '').strip()
        if language and language not in LANGUAGE_NAMES:
            return _error('bad_language', 'Unknown language.')
        upload = request.FILES.get('file')
        if not upload:
            return _error('no_file', 'No file provided.')
        if upload.size > h5p.MAX_FILE_BYTES:
            return _error('too_large', 'The file is larger than 100 MB.')

        folder = f'h5p/{uuid.uuid4().hex}'
        try:
            info = h5p.extract_package(upload, Path(settings.MEDIA_ROOT) / folder)
        except h5p.H5PError as exc:
            return _error(exc.code, exc.detail)
        upload.seek(0)

        first_main = not language and not resource.h5p_packages.filter(language='').exists()
        package = resource.h5p_packages.filter(language=language).first()
        if package is None:
            package = H5PPackage(resource=resource, language=language)
        else:
            package.version += 1
        package.file.save(f'{uuid.uuid4().hex}.h5p', upload, save=False)
        package.folder = folder
        package.title = info.title
        package.main_library = info.main_library
        package.size_bytes = upload.size
        package.uploaded_by = request.user
        package.save()

        if first_main:
            resource.h5p_self_complete = h5p.default_self_complete(info.main_library)
            fields = ['h5p_self_complete']
            if not resource.title and info.title:
                resource.title = info.title[:200]
                fields.append('title')
            resource.save(update_fields=fields)
            if 'title' in fields:
                resync_resource(resource)
        CourseEditHistory.objects.create(
            course=resource.activity.module.course, editor=request.user,
            changes={'h5p_uploaded': {
                'resource': resource.id, 'language': language or 'main',
                'library': info.main_library, 'version': package.version,
            }},
        )
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        language = request.query_params.get('language', '')
        deleted, _ = resource.h5p_packages.filter(language=language).delete()
        if not deleted:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResourceSerializer(resource).data)
