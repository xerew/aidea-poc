import os
import uuid

from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.ai_review.evidence import anonymise
from hub.models import (
    Activity,
    AIReview,
    AssignmentSubmission,
    Course,
    CourseCollaborator,
    Enrollment,
    Resource,
    ReviewExample,
    UserProfile,
)
from hub.serializers.assignments import (
    AssignmentSubmissionSerializer,
    ReviewQueueSerializer,
    latest_ai_review,
)

from .permissions import IsReviewer, can_edit_course

# Attachments a learner may upload with a submission.
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
DOC_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt'}
SUBMISSION_EXTENSIONS = IMAGE_EXTENSIONS | DOC_EXTENSIONS
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def _reviewer_scope(queryset, user):
    """Creators see submissions for courses they authored or co-edit;
    partners/admins see all."""
    if user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR:
        return queryset.filter(
            Q(lesson__module__course__created_by=user)
            | Q(lesson__module__course__collaborators__user=user,
                lesson__module__course__collaborators__role=CourseCollaborator.Role.CO_EDITOR),
        ).distinct()
    return queryset


def can_review(user, submission):
    """Partners/admins review everything; creators only courses they author or co-edit."""
    return (user.profile.user_type != UserProfile.UserType.CONTENT_CREATOR
            or can_edit_course(user, submission.lesson.module.course))


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
            lesson = Activity.objects.select_related('module').get(pk=lesson_pk, module__course_id=pk)
        except Activity.DoesNotExist:
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
            from hub.completion import ensure_resources
            ensure_resources(lesson)
            submission = AssignmentSubmission.objects.create(
                user=request.user, lesson=lesson, text=text, attachments=attachments,
                resource=lesson.resources.filter(type='assignment').first(),
            )
            created = True

        from hub.ai_review.pipeline import queue_review
        queue_review(submission)

        return Response(
            AssignmentSubmissionSerializer(submission, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ResourceAssignmentSubmitView(APIView):
    """POST .../lessons/<lesson_pk>/resources/<resource_pk>/submit-assignment/ —
    learner submits/resubmits to an assignment resource."""

    def post(self, request, pk, lesson_pk, resource_pk):
        if not Enrollment.objects.filter(user=request.user, course_id=pk).exists():
            if not Course.objects.filter(pk=pk).exists():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': 'Not enrolled.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            resource = Resource.objects.select_related('activity__module').get(
                pk=resource_pk, activity_id=lesson_pk,
                activity__module__course_id=pk, type='assignment',
            )
        except Resource.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        text = str(request.data.get('text', '')).strip()
        attachments, err = _clean_attachments(request.data.get('attachments'))
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        if not text and not attachments:
            return Response(
                {'detail': 'Provide text or at least one attachment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = AssignmentSubmission.objects.filter(
            user=request.user, resource=resource,
        ).first()
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
                user=request.user, lesson=resource.activity, resource=resource,
                text=text, attachments=attachments,
            )
            created = True

        from hub.ai_review.pipeline import queue_review
        queue_review(submission)

        return Response(
            AssignmentSubmissionSerializer(submission, context={'request': request}).data,
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

    AI_FILTERS = ('ai_approve', 'ai_unsure', 'flagged')

    def get(self, request):
        wanted = request.query_params.get('filter')
        base = AssignmentSubmission.objects.select_related('user', 'lesson__module__course', 'resource__ai_review_config')
        if wanted == 'auto_approved':
            # Still approved by the AI: no human has approved it since (e.g. after a reopen).
            base = base.filter(status=AssignmentSubmission.Status.APPROVED, reviewed_by__isnull=True,
                               ai_reviews__auto_approved=True).distinct()
        else:
            base = base.filter(status=AssignmentSubmission.Status.PENDING)
        rows = list(_reviewer_scope(base, request.user))
        if wanted in self.AI_FILTERS:
            def keep(sub):
                review = latest_ai_review(sub)
                if review is None or review.status != AIReview.Status.DONE:
                    return False
                return {'ai_approve': review.verdict == AIReview.Verdict.APPROVE,
                        'ai_unsure': review.verdict == AIReview.Verdict.UNSURE,
                        'flagged': review.flagged}[wanted]
            rows = [s for s in rows if keep(s)]
        return Response(ReviewQueueSerializer(rows, many=True).data)


class ReviewQueueCountView(APIView):
    """GET /api/reviews/count/ — how many submissions await this reviewer
    (same scope as the queue); drives the sidebar badge."""
    permission_classes = [IsReviewer]

    def get(self, request):
        pending = _reviewer_scope(
            AssignmentSubmission.objects.filter(status=AssignmentSubmission.Status.PENDING),
            request.user,
        ).count()
        return Response({'pending': pending})


class ReviewActionView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        try:
            submission = AssignmentSubmission.objects.select_related(
                'user', 'lesson__module__course', 'resource__activity__module',
            ).get(pk=pk)
        except AssignmentSubmission.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not can_review(request.user, submission):
            return Response(
                {'detail': 'You can only review submissions to courses you author or co-edit.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if submission.status != AssignmentSubmission.Status.PENDING:
            return Response(
                {'detail': 'Only pending submissions can be reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action')
        feedback = str(request.data.get('feedback', '')).strip()

        from hub.ai_review.pipeline import record_human_verdict
        from hub.assignment_review import ReviewError, approve_submission, request_changes

        if action == 'approve':
            try:
                approve_submission(submission, request.user, feedback)
            except ReviewError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            verdict = 'approve'
        elif action == 'request_changes':
            if not feedback:
                return Response(
                    {'detail': 'feedback is required when requesting changes.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                request_changes(submission, request.user, feedback)
            except ReviewError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            verdict = 'changes_requested'
        else:
            return Response(
                {'detail': "action must be 'approve' or 'request_changes'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record_human_verdict(
            submission, verdict, reason=str(request.data.get('disagreement_reason', '')),
            feedback_used=request.data.get('used_ai_feedback') is True, feedback=feedback,
        )
        return Response(AssignmentSubmissionSerializer(submission).data)


class ReviewExampleView(APIView):
    """POST /api/reviews/<pk>/example/ — use this submission (anonymised) as an
    example for the assignment's AI reviewer."""
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        submission = (AssignmentSubmission.objects
                      .select_related('user', 'lesson__module__course', 'resource')
                      .filter(pk=pk).first())
        if submission is None or not submission.resource_id:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_review(request.user, submission):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        verdict = request.data.get('verdict')
        if verdict not in ('approve', 'changes_requested'):
            return Response({'detail': 'verdict must be approve or changes_requested.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if getattr(getattr(submission.user, 'profile', None), 'ai_training_opt_out', False):
            return Response({'detail': 'This learner opted out of their work being used to improve the AI reviewer.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if submission.resource.ai_review_examples.count() >= 5:
            return Response({'detail': 'This assignment already has 5 examples.'},
                            status=status.HTTP_400_BAD_REQUEST)
        ReviewExample.objects.create(
            resource=submission.resource, text=anonymise(submission.text or '', submission.user)[:8000],
            verdict=verdict, reason=str(request.data.get('reason', ''))[:1000],
            source_submission=submission, created_by=request.user,
        )
        return Response(status=status.HTTP_201_CREATED)


class ReviewReopenView(APIView):
    """POST /api/reviews/<pk>/reopen/ — send an AI-approved submission back to
    the review queue."""
    permission_classes = [IsReviewer]

    def post(self, request, pk):
        submission = (AssignmentSubmission.objects
                      .select_related('user', 'lesson__module__course')
                      .filter(pk=pk).first())
        if submission is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_review(request.user, submission):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        if (submission.status != AssignmentSubmission.Status.APPROVED
                or submission.reviewed_by_id is not None
                or not submission.ai_reviews.filter(auto_approved=True).exists()):
            return Response({'detail': 'Only AI-approved submissions can be reopened.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from hub.assignment_review import reopen_submission
        reopen_submission(submission)
        return Response(AssignmentSubmissionSerializer(submission).data)
