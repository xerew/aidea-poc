from django.contrib.auth.models import User
from django.db import models

from .content import Activity


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING           = 'pending',           'Pending review'
        APPROVED          = 'approved',          'Approved'
        CHANGES_REQUESTED = 'changes_requested', 'Changes requested'

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    lesson       = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='submissions')
    # Repointed to the assignment resource by the data migration; becomes the
    # canonical target in Phase 2 (lesson kept as the rollback window).
    resource     = models.ForeignKey(
        'hub.Resource', on_delete=models.CASCADE, null=True, blank=True, related_name='submissions',
    )
    text         = models.TextField(blank=True)
    # List of attachment blocks: {'type': 'image'|'file'|'video', 'url': str, 'name': str}.
    attachments  = models.JSONField(default=list, blank=True)
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    feedback     = models.TextField(blank=True)
    reviewed_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions',
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')
        ordering = ['submitted_at']

    def __str__(self):
        return f'{self.user.username} -> {self.lesson.title} ({self.status})'
