from django.db import models


class OnboardingDimension(models.Model):
    """One of the AI self-efficacy dimensions (e.g. AI Knowledge, AI Ethics).

    Questions are grouped under a dimension; each dimension yields an average
    score and a self-efficacy band (low/moderate/high).
    """
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Per-language overrides for `name`, e.g. {"el": "…", "fr": "…"}.
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class OnboardingQuestion(models.Model):
    """A single self-efficacy statement rated on the shared 5-point Likert scale.

    There is no correct answer — teachers rate their confidence from 1 (strongly
    disagree) to 5 (strongly agree). Admin-editable and translatable.
    """
    dimension = models.ForeignKey(
        OnboardingDimension, on_delete=models.CASCADE, related_name='questions',
        null=True, blank=True,
    )
    text = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Per-language overrides for `text`, e.g. {"el": "…", "fr": "…"}.
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['dimension__order', 'order']

    def __str__(self):
        return self.text
