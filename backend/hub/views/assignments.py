import os
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AssignmentSubmission, Course, Enrollment, Lesson, UserProfile
from hub.serializers.assignments import AssignmentSubmissionSerializer, ReviewQueueSerializer

from .permissions import IsReviewer

# Attachments a learner may upload with a submission.
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
DOC_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt'}
SUBMISSION_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def _reviewer_scope(queryset, user):
    """Creators see their own courses' submissions; partners/admins see all."""
    if user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR:
        return queryset.filter(lesson__module__course__created_by=user)
    return queryset


def _clean_attachments(raw):
    """Validate and normalise the attachments payload.

    Returns (attachments, error). Each attachment is
    {'type': 'image'|'file'|'video', 'url': str, 'name': str}.
    """
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
        if atype not in ('image', 'file', 'video') or not url:
            return None, 'Each attachment needs a valid type and url.'
        cleaned.append({'type': atype, 'url': url, 'name': str(item.get('name', '')).strip()})
    return cleaned, None


class AssignmentSubmitView(APIView):
    """POST /courses/<pk>/lessons/<lesson_pk>/submit-assignment/ — learner submits/resubmits."""

    def post(self, request, pk, lesson_pk):
        if not Enrollment.objects.filter(user=request.user, course_id=pk).exists():
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            lesson = Lesson.objects.select_related('module').get(pk=lesson_pk, module__course_id=pk)
        except Lesson.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if lesson.lesson_type != 'assignment':
            return Response(
                {'detail': 'Only assignment lessons accept submissions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = str(request.data.get('text', '')).strip()
        attachments, err = _clean_attachments(request.data.get('attachments'))
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        if not text and not attachments:
            return Response(
                {'detail': 'Provide text or at least one attachment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = AssignmentSubmission.objects.filter(user=request.user, lesson=lesson).first()
        if submission and submission.status == AssignmentSubmission.Status.APPROVED:
            return Response(
                {'detail': 'This assignment is already approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission:
            submission.text = text
            submission.attachments = attachments
            submission.status = AssignmentSubmission.Status.PENDING
            submission.save(update_fields=['text', 'attachments', 'status', 'updated_at'])
            created = False
        else:
            submission = AssignmentSubmission.objects.create(
                user=request.user, lesson=lesson, text=text, attachments=attachments,
            )
            created = True

        if lesson.module.llm_review_enabled:
            from hub.llm_review import review_submission
            review_submission(submission)  # stub: returns None, humans review

        return Response(
            AssignmentSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SubmissionUploadView(APIView):
    """POST /courses/<pk>/lessons/<lesson_pk>/submission-upload/ — store one
    attachment for an enrolled learner and return its URL, name and type."""

    def post(self, request, pk, lesson_pk):
        if not Enrollment.objects.filter(user=request.user, course_id=pk).exists():
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in SUBMISSION_EXTENSIONS:
            allowed = ', '.join(sorted(SUBMISSION_EXTENSIONS))
            return Response(
                {'detail': f'File type not allowed. Allowed: {allowed}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > MAX_UPLOAD_BYTES:
            return Response({'detail': 'File too large (max 20 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        path = default_storage.save(f'submission_uploads/{uuid.uuid4().hex}{ext}', file)
        return Response(
            {
                'url': request.build_absolute_uri(default_storage.url(path)),
                'name': file.name,
                'type': 'image' if ext in IMAGE_EXTENSIONS else 'file',
            },
            status=status.HTTP_201_CREATED,
        )


class ReviewQueueView(APIView):
    permission_classes = [IsReviewer]

    def get(self, request):
        queryset = _reviewer_scope(
            AssignmentSubmission.objects.filter(status=AssignmentSubmission.Status.PENDING)
            .select_related('user', 'lesson__module__course'),
            request.user,
        )
        return Response(ReviewQueueSerializer(queryset, many=True).data)


class ReviewActionView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        try:
            submission = AssignmentSubmission.objects.select_related(
                'user', 'lesson__module__course',
            ).get(pk=pk)
        except AssignmentSubmission.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        course = submission.lesson.module.course
        if (
            request.user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR
            and course.created_by_id != request.user.id
        ):
            return Response(
                {'detail': 'You can only review submissions to your own courses.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if submission.status != AssignmentSubmission.Status.PENDING:
            return Response(
                {'detail': 'Only pending submissions can be reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action')
        feedback = str(request.data.get('feedback', '')).strip()

        if action == 'approve':
            enrollment = Enrollment.objects.filter(user=submission.user, course=course).first()
            if enrollment is None:
                return Response(
                    {'detail': 'The learner is no longer enrolled in this course.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from django.db import transaction

            from hub.completion import record_lesson_completion
            with transaction.atomic():
                submission.status = AssignmentSubmission.Status.APPROVED
                if feedback:
                    submission.feedback = feedback
                submission.reviewed_by = request.user
                submission.reviewed_at = timezone.now()
                submission.save()

                record_lesson_completion(
                    submission.user, enrollment, submission.lesson,
                    engagement_data={'submission': submission.text},
                    advance_only=True,
                )
        elif action == 'request_changes':
            if not feedback:
                return Response(
                    {'detail': 'feedback is required when requesting changes.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            submission.status = AssignmentSubmission.Status.CHANGES_REQUESTED
            submission.feedback = feedback
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.save()
        else:
            return Response(
                {'detail': "action must be 'approve' or 'request_changes'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(AssignmentSubmissionSerializer(submission).data)
