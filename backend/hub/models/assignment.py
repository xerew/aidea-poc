from django.contrib.auth.models import User
from django.db import models

from .content import Lesson


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        PENDING           = 'pending',           'Pending review'
        APPROVED          = 'approved',          'Approved'
        CHANGES_REQUESTED = 'changes_requested', 'Changes requested'

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='submissions')
    text         = models.TextField()
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
