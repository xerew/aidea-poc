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
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.score:.2f})'
