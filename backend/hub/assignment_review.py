"""Approving / requesting changes / reopening an assignment submission —
shared by human reviewers and the AI reviewer's auto-approve."""
from django.db import transaction
from django.utils import timezone

from hub.models import AssignmentSubmission, Enrollment, ResourceProgress


class ReviewError(Exception):
    pass


def approve_submission(submission, reviewer, feedback=''):
    course = submission.lesson.module.course
    enrollment = Enrollment.objects.filter(user=submission.user, course=course).first()
    if enrollment is None:
        raise ReviewError('The learner is no longer enrolled in this course.')
    from hub.completion import record_lesson_completion, record_resource_completion
    with transaction.atomic():
        submission.status = AssignmentSubmission.Status.APPROVED
        if not submission.first_review_status:
            submission.first_review_status = AssignmentSubmission.Status.APPROVED
        if feedback:
            submission.feedback = feedback
        submission.reviewed_by = reviewer
        submission.reviewed_at = timezone.now()
        submission.save()
        if submission.resource_id:
            record_resource_completion(submission.user, enrollment, submission.resource,
                                       engagement_data={'submission': submission.text}, advance_only=True)
        else:
            record_lesson_completion(submission.user, enrollment, submission.lesson,
                                     engagement_data={'submission': submission.text}, advance_only=True)
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)


def request_changes(submission, reviewer, feedback):
    submission.status = AssignmentSubmission.Status.CHANGES_REQUESTED
    if not submission.first_review_status:
        submission.first_review_status = AssignmentSubmission.Status.CHANGES_REQUESTED
    submission.feedback = feedback
    submission.reviewed_by = reviewer
    submission.reviewed_at = timezone.now()
    submission.save()
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)


def reopen_submission(submission):
    """Undo an approval: the submission waits for a human again and its
    resource is no longer complete."""
    from hub.completion import recompute_course_progress
    with transaction.atomic():
        submission.status = AssignmentSubmission.Status.PENDING
        submission.reviewed_by = None
        submission.reviewed_at = None
        submission.save()
        if submission.resource_id:
            ResourceProgress.objects.filter(user=submission.user, resource=submission.resource).delete()
        enrollment = Enrollment.objects.filter(user=submission.user, course=submission.lesson.module.course).first()
        if enrollment:
            if recompute_course_progress(submission.user, enrollment) < 100 and enrollment.completed_at:
                enrollment.completed_at = None
                enrollment.save(update_fields=['completed_at'])
    from hub.emails import send_assignment_reviewed_email
    send_assignment_reviewed_email(submission)
