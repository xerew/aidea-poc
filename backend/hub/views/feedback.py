import os
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Feedback, UserProfile
from hub.serializers.feedback import FeedbackSerializer

from .permissions import IsAdmin

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
DOC_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt'}
FEEDBACK_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def _clean_attachments(raw):
    """Validate the attachments payload → (list, error)."""
    if raw in (None, ''):
        return [], None
    if not isinstance(raw, list):
        return None, 'attachments must be a list.'
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            return None, 'Each attachment must be an object.'
        atype = item.get('type')
        url = str(item.get('url', '')).strip()
        if atype not in ('image', 'file', 'link') or not url:
            return None, 'Each attachment needs a valid type and url.'
        cleaned.append({'type': atype, 'url': url, 'name': str(item.get('name', '')).strip()})
    return cleaned, None


def _stream_for(user):
    is_partner = getattr(getattr(user, 'profile', None), 'user_type', None) == UserProfile.UserType.AIDEA_PARTNER
    return Feedback.Stream.PARTNER if is_partner else Feedback.Stream.USER


class FeedbackView(APIView):
    """POST /api/feedback/ — submit feedback (any signed-in user)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        category = request.data.get('category')
        if category not in Feedback.Category.values:
            return Response({'detail': 'Invalid category.'}, status=status.HTTP_400_BAD_REQUEST)

        message = str(request.data.get('message', '')).strip()
        if not message:
            return Response({'detail': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        attachments, err = _clean_attachments(request.data.get('attachments'))
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        feedback = Feedback.objects.create(
            user=request.user, stream=_stream_for(request.user),
            category=category, message=message, attachments=attachments,
        )
        from hub.emails import send_feedback_email
        send_feedback_email(feedback)
        return Response(
            FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED,
        )


class FeedbackMineView(APIView):
    """GET /api/feedback/mine/ — the caller's own submissions with status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Feedback.objects.filter(user=request.user)
        return Response(FeedbackSerializer(items, many=True).data)


class FeedbackUploadView(APIView):
    """POST /api/feedback/upload/ — store one image/file attachment."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in FEEDBACK_EXTENSIONS:
            allowed = ', '.join(sorted(FEEDBACK_EXTENSIONS))
            return Response(
                {'detail': f'File type not allowed. Allowed: {allowed}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_UPLOAD_BYTES:
            return Response({'detail': 'File too large (max 20 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        path = default_storage.save(f'feedback_uploads/{uuid.uuid4().hex}{ext}', file)
        return Response(
            {
                'url': request.build_absolute_uri(default_storage.url(path)),
                'name': file.name,
                'type': 'image' if ext in IMAGE_EXTENSIONS else 'file',
            },
            status=status.HTTP_201_CREATED,
        )


class AdminFeedbackListView(APIView):
    """GET /api/admin/feedback/ — all feedback for triage (admins only)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        items = Feedback.objects.select_related('user', 'user__profile').all()
        return Response(FeedbackSerializer(items, many=True).data)


class AdminFeedbackDetailView(APIView):
    """PATCH /api/admin/feedback/<pk>/ — set an item's status (admins only)."""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            feedback = Feedback.objects.get(pk=pk)
        except Feedback.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        if new_status not in Feedback.Status.values:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        reason = str(request.data.get('rejection_reason', '')).strip()
        if new_status == Feedback.Status.REJECTED and not reason:
            return Response(
                {'detail': 'A reason is required when rejecting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feedback.status = new_status
        feedback.rejection_reason = reason if new_status == Feedback.Status.REJECTED else ''
        feedback.reviewed_by = request.user
        feedback.reviewed_at = timezone.now()
        feedback.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at', 'updated_at'])

        return Response(FeedbackSerializer(feedback).data)
