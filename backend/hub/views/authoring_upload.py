import os
import uuid

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsContentCreator

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class AuthoringUploadView(APIView):
    """POST /api/authoring/upload/ — store a lesson asset, return its absolute URL."""

    permission_classes = [IsContentCreator]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
            return Response(
                {'error': f'File type not allowed. Allowed: {allowed}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_UPLOAD_BYTES:
            return Response({'error': 'File too large (max 20 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        path = default_storage.save(f'lesson_uploads/{uuid.uuid4().hex}{ext}', file)
        return Response(
            {'url': request.build_absolute_uri(default_storage.url(path))},
            status=status.HTTP_201_CREATED,
        )
