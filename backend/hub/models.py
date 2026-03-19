from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER = 'teacher', 'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN = 'admin', 'Admin'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials = models.CharField(max_length=4, blank=True)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'


class LearningPillar(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER     = 'beginner',     'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED     = 'advanced',     'Advanced'

    title              = models.CharField(max_length=200)
    description        = models.TextField(blank=True)
    pillar             = models.ForeignKey(LearningPillar, on_delete=models.PROTECT, related_name='courses')
    level              = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    duration_hours     = models.PositiveSmallIntegerField(default=0)
    learning_outcomes  = models.JSONField(default=list, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pillar', 'title']

    def __str__(self):
        return self.title


class Module(models.Model):
    title            = models.CharField(max_length=200)
    description      = models.TextField(blank=True)
    course           = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order            = models.PositiveSmallIntegerField(default=0)
    duration_minutes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} — {self.title}'


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
