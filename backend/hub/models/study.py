from django.contrib.auth.models import User
from django.db import models

from .pathway import LearningPath


class StudyConfig(models.Model):
    """Singleton settings for the adaptive-vs-fixed comparison study."""
    enabled        = models.BooleanField(default=False)
    control_path   = models.ForeignKey(
        LearningPath, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', help_text='Fixed course sequence given to the control (fixed) group.',
    )
    post_test_open = models.BooleanField(
        default=False, help_text='When on, participants who finished the pre-test can take the post-test.',
    )

    class Meta:
        verbose_name = 'Study configuration'

    def __str__(self):
        return f'Study ({"enabled" if self.enabled else "disabled"})'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StudyPreregistration(models.Model):
    """Singleton open-science pre-registration: a locked, timestamped snapshot of
    the study design (config + questions) plus the stated hypothesis, so the
    analysis plan is fixed before data collection."""
    hypothesis  = models.TextField(blank=True)
    snapshot    = models.JSONField(default=dict, blank=True)  # design at lock time
    locked_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Study pre-registration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Pre-registration ({"locked" if self.locked_at else "unlocked"})'


class StudyAssessmentQuestion(models.Model):
    """One question of the dedicated pre/post knowledge test."""
    text  = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]


class StudyAssessmentOption(models.Model):
    question   = models.ForeignKey(
        StudyAssessmentQuestion, on_delete=models.CASCADE, related_name='options',
    )
    text       = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order      = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.text} ({"correct" if self.is_correct else "distractor"})'


class StudyParticipant(models.Model):
    class Group(models.TextChoices):
        ADAPTIVE = 'adaptive', 'Adaptive'
        FIXED    = 'fixed',    'Fixed'

    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='study')
    in_study           = models.BooleanField(default=False)  # False = consented out
    group              = models.CharField(max_length=10, choices=Group.choices, blank=True)
    consented_at       = models.DateTimeField(null=True, blank=True)
    pre_score          = models.IntegerField(null=True, blank=True)
    pre_completed_at   = models.DateTimeField(null=True, blank=True)
    post_score         = models.IntegerField(null=True, blank=True)
    post_completed_at  = models.DateTimeField(null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} — {self.group or "excluded"}'

    @property
    def gain(self):
        if self.pre_score is None or self.post_score is None:
            return None
        return self.post_score - self.pre_score
