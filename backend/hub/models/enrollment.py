from django.contrib.auth.models import User
from django.db import models

from .content import Course, Module


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    current_module = models.ForeignKey(
        Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    progress_pct = models.PositiveSmallIntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-last_accessed_at']

    def __str__(self):
        return f'{self.user.username} → {self.course.title} ({self.progress_pct}%)'
