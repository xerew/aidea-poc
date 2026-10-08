"""Measured learning activity — see
docs/superpowers/specs/2026-10-01-learning-analytics-design.md.

ResourceVisit: one row per learner, per resource, per activity-page visit, with
active / on-screen seconds accumulated from the page's messages.
LearningEvent: one row per discrete moment (video play/seek, PDF download,
quiz answer …). Module and activity times are derived from visits, never stored."""
from django.contrib.auth.models import User
from django.db import models


class ResourceVisit(models.Model):
    class Device(models.TextChoices):
        DESKTOP = 'desktop', 'Desktop'
        TABLET  = 'tablet',  'Tablet'
        MOBILE  = 'mobile',  'Mobile'

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_visits')
    resource = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='visits')
    # Denormalised from resource for fast per-course / per-module queries.
    activity = models.ForeignKey('hub.Activity', on_delete=models.CASCADE, related_name='+')
    module   = models.ForeignKey('hub.Module', on_delete=models.CASCADE, related_name='+')
    course   = models.ForeignKey('hub.Course', on_delete=models.CASCADE, related_name='+')
    visit_key = models.UUIDField()  # made by the browser: one per resource per page visit
    page_key  = models.UUIDField()  # made by the browser: one per activity-page visit
    started_at   = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    active_seconds   = models.PositiveIntegerField(default=0)
    visible_seconds  = models.PositiveIntegerField(default=0)
    completed_during = models.BooleanField(default=False)
    language = models.CharField(max_length=8, blank=True)
    device   = models.CharField(max_length=10, choices=Device.choices, blank=True)
    local_hour        = models.PositiveSmallIntegerField(null=True, blank=True)
    tz_offset_minutes = models.SmallIntegerField(null=True, blank=True)  # minutes ahead of UTC
    # Videos: {covered_pct, furthest_s, duration_s} for this visit.
    media_progress = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'visit_key')
        indexes = [
            models.Index(fields=['course', 'user']),
            models.Index(fields=['resource', 'user']),
            models.Index(fields=['user', 'last_seen_at']),
        ]

    def __str__(self):
        return f'{self.user.username} on resource {self.resource_id} at {self.started_at}'


class LearningEvent(models.Model):
    class Type(models.TextChoices):
        VIDEO_PLAY   = 'video_play',   'Video play'
        VIDEO_PAUSE  = 'video_pause',  'Video pause'
        VIDEO_SEEK   = 'video_seek',   'Video seek'
        VIDEO_ENDED  = 'video_ended',  'Video ended'
        PDF_OPEN     = 'pdf_open',     'PDF opened'
        PDF_DOWNLOAD = 'pdf_download', 'PDF downloaded'
        IMAGE_OPEN   = 'image_open',   'Image opened'
        QUIZ_ANSWER  = 'quiz_answer',  'Quiz answer'
        H5P_ANSWER   = 'h5p_answer',   'H5P answer'
        H5P_ATTEMPT  = 'h5p_attempt',  'H5P attempt finished'
        H5P_ERROR    = 'h5p_error',    'H5P failed to load'

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_events')
    resource = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='events')
    visit    = models.ForeignKey(
        ResourceVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='events',
    )
    course    = models.ForeignKey('hub.Course', on_delete=models.CASCADE, related_name='+')
    event_key = models.UUIDField()  # made by the browser, so a resent event is stored once
    event_type  = models.CharField(max_length=20, choices=Type.choices)
    occurred_at = models.DateTimeField()
    # e.g. {position} · {from, to} · {question_index, selected, seconds_on_question}
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'event_key')
        ordering = ['occurred_at']
        indexes = [
            models.Index(fields=['course', 'user']),
            models.Index(fields=['resource', 'event_type']),
        ]

    def __str__(self):
        return f'{self.user.username} {self.event_type} at {self.occurred_at}'
