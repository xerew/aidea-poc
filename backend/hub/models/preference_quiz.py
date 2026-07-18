from django.db import models

from .user import UserProfile


class PreferenceQuestion(models.Model):
    text      = models.CharField(max_length=300)
    order     = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class PreferenceOption(models.Model):
    question = models.ForeignKey(
        PreferenceQuestion, on_delete=models.CASCADE, related_name='options',
    )
    text     = models.CharField(max_length=300)
    maps_to  = models.CharField(max_length=20, choices=UserProfile.LearningStyle.choices)
    order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.text} -> {self.maps_to}'
