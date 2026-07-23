from django.db import models


class OnboardingQuestion(models.Model):
    """A competency knowledge-check question shown during onboarding.

    Admin-editable so the competency assessment can change without a code
    release. The competency score is the sum of the chosen options' points.
    """

    text = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

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

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.text} ({self.score})'
