from django.contrib.auth.models import User
from django.db import models

from .content import Course


class LearningPath(models.Model):
    name           = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True)
    description    = models.TextField(blank=True)
    competency_min = models.PositiveSmallIntegerField(default=0)
    competency_max = models.PositiveSmallIntegerField(default=6)
    courses        = models.ManyToManyField(Course, through='LearningPathCourse', blank=True)

    class Meta:
        ordering = ['competency_min']

    def __str__(self):
        return self.name


class LearningPathCourse(models.Model):
    path   = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='path_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('path', 'course')

    def __str__(self):
        return f'{self.path.name} — {self.course.title} (#{self.order})'


class UserLearningPath(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='learning_path')
    path        = models.ForeignKey(LearningPath, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} → {self.path.name}'
