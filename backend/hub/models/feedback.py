from django.contrib.auth.models import User
from django.db import models


class Feedback(models.Model):
    class Stream(models.TextChoices):
        USER    = 'user',    'User feedback'
        PARTNER = 'partner', 'Partner feedback'

    class Category(models.TextChoices):
        BUG             = 'bug',             'Bug'
        SUGGESTION      = 'suggestion',      'Suggestion'
        FEEDBACK        = 'feedback',        'Feedback'
        FEATURE_REQUEST = 'feature_request', 'Feature request'
        CONTENT_ISSUE   = 'content_issue',   'Content issue'

    class Status(models.TextChoices):
        NEW         = 'new',         'New'
        REVIEWING   = 'reviewing',   'Under review'
        IN_PROGRESS = 'in_progress', 'In progress'
        RESOLVED    = 'resolved',    'Resolved'
        REJECTED    = 'rejected',    'Rejected'

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    stream           = models.CharField(max_length=10, choices=Stream.choices, default=Stream.USER)
    category         = models.CharField(max_length=20, choices=Category.choices)
    message          = models.TextField()
    # List of attachment blocks: {'type': 'image'|'file'|'link', 'url': str, 'name': str}.
    attachments      = models.JSONField(default=list, blank=True)
    status           = models.CharField(max_length=15, choices=Status.choices, default=Status.NEW)
    rejection_reason = models.TextField(blank=True)
    reviewed_by      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_feedback',
    )
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_category_display()} by {self.user.username} ({self.status})'
