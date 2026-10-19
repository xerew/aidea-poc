from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub import presentation
from hub.models import CourseEditHistory, PresentationFile, Resource
from hub.serializers import ResourceSerializer
from hub.translation import LANGUAGE_NAMES
from hub.translation_sync import resync_resource

from .permissions import IsContentCreator, can_edit_course


def _error(code, detail):
    return Response({'code': code, 'detail': detail}, status=status.HTTP_400_BAD_REQUEST)


class AuthoringPresentationView(APIView):
    """POST (multipart: file, language) — upload or replace a presentation
    resource's .pptx for one language ('' = main deck). DELETE ?language= —
    remove it. Replaced and removed files are deleted from disk."""

    permission_classes = [IsContentCreator]

    def _resource(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource = (
            Resource.objects.select_related('activity__module__course')
            .filter(pk=resource_pk, activity_id=lesson_pk,
                    activity__module_id=module_pk, activity__module__course_id=pk)
            .first()
        )
        if resource is None:
            return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_edit_course(request.user, resource.activity.module.course):
            return None, Response({'detail': 'You cannot edit this course.'}, status=status.HTTP_403_FORBIDDEN)
        if resource.type != Resource.Type.PRESENTATION:
            return None, _error('not_presentation', 'This resource is not a presentation.')
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
        if upload.size > settings.PRESENTATION_MAX_MB * 1024 * 1024:
            return _error('too_large', f'The file is larger than {settings.PRESENTATION_MAX_MB} MB.')
        try:
            info = presentation.check_pptx(upload)
        except presentation.PresentationError as exc:
            return _error(exc.code, exc.detail)

        first_main = not language and not resource.presentation_files.filter(language='').exists()
        deck = resource.presentation_files.filter(language=language).first()
        old_name = None
        if deck is None:
            deck = PresentationFile(resource=resource, language=language)
        else:
            old_name = deck.file.name
            deck.version += 1
        deck.file.save('deck.pptx', upload, save=False)
        deck.title = info.title or Path(upload.name).stem[:255]
        deck.slide_count = info.slide_count
        deck.size_bytes = upload.size
        deck.uploaded_by = request.user
        deck.save()
        if old_name and old_name != deck.file.name:
            default_storage.delete(old_name)

        if first_main and not resource.title and deck.title:
            resource.title = deck.title[:200]
            resource.save(update_fields=['title'])
            resync_resource(resource)
        CourseEditHistory.objects.create(
            course=resource.activity.module.course, editor=request.user,
            changes={'presentation_uploaded': {
                'resource': resource.id, 'language': language or 'main',
                'slides': deck.slide_count, 'version': deck.version,
            }},
        )
        return Response(ResourceSerializer(resource).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, module_pk, lesson_pk, resource_pk):
        resource, failure = self._resource(request, pk, module_pk, lesson_pk, resource_pk)
        if failure:
            return failure
        deck = resource.presentation_files.filter(language=request.query_params.get('language', '')).first()
        if deck is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        deck.delete()   # the post_delete signal removes the file
        return Response(ResourceSerializer(resource).data)
