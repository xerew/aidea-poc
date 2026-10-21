from django.contrib.auth.models import User
from django.db import models

from .content import Activity


class LessonSession(models.Model):
    """Records the moment a teacher opens a lesson — used to compute time_spent_seconds."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_sessions')
    lesson     = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} opened {self.lesson.title} at {self.started_at}'


class LearnerActivityConfig(models.Model):
    """Singleton config for learner activity tracking and the AI competency rule
    (docs/superpowers/specs/2026-10-21-competency-performance-design.md)."""
    # Competency: a course counts as passed at this first-attempt performance (0–1).
    quiz_pass_threshold     = models.FloatField(default=0.7)

    # Slow-pace penalty and idle decay
    slow_ratio_threshold = models.FloatField(default=3.0)
    slow_penalty         = models.PositiveSmallIntegerField(default=1)
    idle_decay_days      = models.PositiveSmallIntegerField(default=30)
    idle_decay_points    = models.PositiveSmallIntegerField(default=1)
    # Separate switches: the slow-pace penalty on course completion, and the nightly idle decay.
    slow_penalty_enabled = models.BooleanField(default=True)
    idle_decay_enabled   = models.BooleanField(default=False)

    # Learning analytics: when off, the activity page stops sending time and
    # interaction data (see hub/tracking.py). Existing data is kept.
    tracking_enabled = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Learner activity settings'
