from django.contrib.auth.models import User
from django.db import models

from .content import Lesson


class LessonSession(models.Model):
    """Records the moment a teacher opens a lesson — used to compute time_spent_seconds."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_sessions')
    lesson     = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} opened {self.lesson.title} at {self.started_at}'


class LearnerActivityConfig(models.Model):
    """Singleton config for learner activity tracking and quiz-competency weighting."""
    quiz_affects_competency = models.BooleanField(default=False)
    quiz_pass_threshold     = models.FloatField(default=0.7)
    quiz_weight_pass        = models.FloatField(default=1.0)
    quiz_weight_fail        = models.FloatField(default=0.5)

    # Decay (see docs/superpowers/specs/2026-07-19-competency-decay-design.md)
    decay_enabled        = models.BooleanField(default=True)
    slow_ratio_threshold = models.FloatField(default=3.0)
    slow_penalty         = models.PositiveSmallIntegerField(default=1)
    idle_decay_days      = models.PositiveSmallIntegerField(default=30)
    idle_decay_points    = models.PositiveSmallIntegerField(default=1)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'LearnerActivityConfig (quiz_affects_competency={self.quiz_affects_competency})'
