from django.contrib.auth.models import User
from django.db import models


class AccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        APPROVED = 'approved', 'Approved'
        DENIED   = 'denied',   'Denied'

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='access_requests')
    message       = models.TextField()
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    denial_reason = models.TextField(blank=True)
    denial_seen   = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    reviewed_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_requests',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.status}'
