from django.contrib.auth.models import User
from django.db import models
from pgvector.django import VectorField

from .content import Course


class CourseEmbedding(models.Model):
    course      = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='embedding')
    embedding   = VectorField(dimensions=384)
    computed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Embedding for {self.course.title}'


class CourseRecommendation(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='recommendations')
    score       = models.FloatField()
    reason      = models.CharField(max_length=200)
    source      = models.CharField(max_length=20, default='personal')
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.score:.2f})'


class CourseView(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_views')
    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_views')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} viewed {self.course.title}'


class RecommendationEvent(models.Model):
    class EventType(models.TextChoices):
        SHOWN     = 'shown',     'Shown'
        CLICKED   = 'clicked',   'Clicked'
        ENROLLED  = 'enrolled',  'Enrolled'
        COMPLETED = 'completed', 'Completed'

    user             = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recommendation_events',
    )
    course           = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='recommendation_events',
    )
    event_type       = models.CharField(max_length=20, choices=EventType.choices)
    rank             = models.PositiveSmallIntegerField(default=0)
    source           = models.CharField(max_length=20)
    weights_snapshot = models.JSONField(default=dict)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} {self.event_type} {self.course.title}'


class RecommendationConfig(models.Model):
    # Signal weights (implicit behaviour)
    w_completed = models.FloatField(default=1.0)
    w_deep      = models.FloatField(default=0.7)
    w_active    = models.FloatField(default=0.4)
    w_enrolled  = models.FloatField(default=0.2)
    w_abandoned = models.FloatField(default=-0.1)
    w_lesson    = models.FloatField(default=0.03)
    w_view      = models.FloatField(default=0.1)
    # Blend weights
    alpha       = models.FloatField(default=0.3)
    beta        = models.FloatField(default=0.5)
    gamma       = models.FloatField(default=0.2)
    style_boost = models.FloatField(default=1.2)
    # Bandit config
    bandit_active   = models.BooleanField(default=False)
    n_min           = models.IntegerField(default=200)
    n_full          = models.IntegerField(default=1000)
    learning_rate   = models.FloatField(default=0.01)
    reward_click    = models.FloatField(default=0.3)
    reward_enroll   = models.FloatField(default=0.5)
    reward_complete = models.FloatField(default=1.0)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'RecommendationConfig (α={self.alpha}, β={self.beta}, γ={self.gamma})'
