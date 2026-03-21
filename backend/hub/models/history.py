from django.contrib.auth.models import User
from django.db import models

from .content import Course


class CourseEditHistory(models.Model):
    course    = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='edit_history')
    editor    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='course_edits')
    edited_at = models.DateTimeField(auto_now_add=True)
    changes   = models.JSONField(default=dict)

    class Meta:
        ordering = ['-edited_at']

    def __str__(self):
        return f'{self.editor} edited "{self.course}" at {self.edited_at:%Y-%m-%d %H:%M}'
