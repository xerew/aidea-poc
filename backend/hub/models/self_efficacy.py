from django.contrib.auth.models import User
from django.db import models


class SelfEfficacyConfig(models.Model):
    """Singleton admin switch. When `retake_open` is True, teachers who already
    completed the assessment may take it again — but only once per window.
    `retake_opened_at` records when the current window was opened so a teacher
    who already retook within it cannot retake again (and admins can see when
    they last opened it)."""
    retake_open = models.BooleanField(default=False)
    retake_opened_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Self-efficacy configuration'


class SelfEfficacyAttempt(models.Model):
    """An immutable snapshot of one completed assessment: the chosen answers and
    the resulting scores. Keeping a row per completion lets admins compare a
    teacher's self-efficacy over time."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='self_efficacy_attempts',
    )
    answers = models.JSONField(default=dict)              # {question_id: 1-5}
    dimension_scores = models.JSONField(default=dict)     # {slug: {average, band}}
    overall_average = models.FloatField(null=True, blank=True)
    overall_band = models.CharField(max_length=10, blank=True)
    competency_score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} — {self.overall_band or "?"} @ {self.created_at:%Y-%m-%d}'
