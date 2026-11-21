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
    # `path` gives the pathway its competency-band name/description; the actual
    # ordered course list is personalised per teacher in `course_ids`.
    path        = models.ForeignKey(LearningPath, on_delete=models.PROTECT)
    course_ids  = models.JSONField(default=list, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} → {self.path.name}'


class PathwayCourseChange(models.Model):
    """A course published or unpublished since pathways were last rebuilt. Admins
    see the pending list and rebuild everyone's pathway when they choose."""
    class Change(models.TextChoices):
        PUBLISHED   = 'published',   'Published'
        UNPUBLISHED = 'unpublished', 'Unpublished'

    course       = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    course_title = models.CharField(max_length=255)
    change       = models.CharField(max_length=20, choices=Change.choices)
    changed_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    changed_at   = models.DateTimeField(auto_now_add=True)
    applied_at   = models.DateTimeField(null=True, blank=True)   # set when a pathway rebuild took it in

    class Meta:
        ordering = ['-changed_at', '-id']

    def __str__(self):
        return f'{self.course_title} {self.change}'
