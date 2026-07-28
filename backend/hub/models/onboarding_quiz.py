from django.db import models


class OnboardingConfig(models.Model):
    """Singleton holding the per-language translation status of the onboarding
    assessment: {lang_code: 'pending'|'done'|'reviewed'|'failed'}."""
    translation_status = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Onboarding configuration'


class OnboardingQuestion(models.Model):
    """A competency knowledge-check question shown during onboarding.

    Admin-editable so the competency assessment can change without a code
    release. The competency score is the sum of the chosen options' points.
    """

    text = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Per-language overrides for `text`, e.g. {"el": "…", "fr": "…"}.
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class OnboardingOption(models.Model):
    question = models.ForeignKey(
        OnboardingQuestion, on_delete=models.CASCADE, related_name='options',
    )
    text = models.CharField(max_length=300)
    score = models.PositiveSmallIntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)
    # Per-language overrides for `text`, e.g. {"el": "…", "fr": "…"}.
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.text} ({self.score})'
