"""Records for the admin per-user activity page (spec 2026-11-21-user-activity-page):
logins (time, device, browser; never an IP address) and, in PlatformAction,
platform actions that leave no other trace."""
from django.contrib.auth.models import User
from django.db import models


class LoginRecord(models.Model):
    class Device(models.TextChoices):
        DESKTOP = 'desktop', 'Desktop'
        TABLET  = 'tablet',  'Tablet'
        MOBILE  = 'mobile',  'Mobile'

    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_records')
    at      = models.DateTimeField(auto_now_add=True)
    device  = models.CharField(max_length=10, choices=Device.choices, blank=True)
    browser = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['-at']
        indexes = [models.Index(fields=['user', 'at'])]

    def __str__(self):
        return f'{self.user.username} signed in at {self.at:%Y-%m-%d %H:%M}'


class PlatformAction(models.Model):
    """Platform actions that leave no other trace, recorded from 2026-11-21 on.
    `label` keeps a title snapshot (course title, or the target username for a
    role change) so the entry still reads right after a deletion."""
    class Kind(models.TextChoices):
        TRANSLATION_REQUESTED = 'translation_requested', 'Translation requested'
        RESOURCE_EDITED       = 'resource_edited',       'Resource edited'
        RESOURCE_DELETED      = 'resource_deleted',      'Resource deleted'
        COURSE_DELETED        = 'course_deleted',        'Course deleted'
        COLLABORATOR_ADDED    = 'collaborator_added',    'Collaborator added'
        COLLABORATOR_REMOVED  = 'collaborator_removed',  'Collaborator removed'
        ROLE_CHANGED          = 'role_changed',          'Role changed'
        AI_REVIEW_SAVED       = 'ai_review_saved',       'AI reviewer set-up saved'
        PATHWAYS_REBUILT      = 'pathways_rebuilt',      'Pathways rebuilt'

    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='platform_actions')
    at      = models.DateTimeField(auto_now_add=True)
    kind    = models.CharField(max_length=30, choices=Kind.choices)
    course  = models.ForeignKey('hub.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    label   = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-at']
        indexes = [models.Index(fields=['user', 'at'])]

    def __str__(self):
        return f'{self.user.username}: {self.get_kind_display()} ({self.label})'
