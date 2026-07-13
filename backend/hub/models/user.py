from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER         = 'teacher',         'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN           = 'admin',           'Admin'

    class SubjectArea(models.TextChoices):
        STEM       = 'stem',       'STEM'
        HUMANITIES = 'humanities', 'Humanities'
        LANGUAGES  = 'languages',  'Languages'
        ARTS       = 'arts',       'Arts'
        GENERAL    = 'general',    'General / Multiple'

    class TeachingLevel(models.TextChoices):
        PRIMARY    = 'primary',    'Primary (K-6)'
        SECONDARY  = 'secondary',  'Secondary (7-12)'
        HIGHER_ED  = 'higher_ed',  'Higher Education'
        VOCATIONAL = 'vocational', 'Vocational'
        ADULT_ED   = 'adult_ed',   'Adult Education'

    class LearningStyle(models.TextChoices):
        VIDEO       = 'video',       'Video'
        TEXT        = 'text',        'Text'
        VISUAL      = 'visual',      'Visual'
        INTERACTIVE = 'interactive', 'Interactive'

    class WeeklyGoal(models.TextChoices):
        LT1 = 'lt1', 'Under 1 hour'
        H12 = '1_2', '1-2 hours'
        H25 = '2_5', '2-5 hours'
        GT5 = 'gt5', '5+ hours'

    class Gender(models.TextChoices):
        MALE           = 'male',           'Male'
        FEMALE         = 'female',         'Female'
        PREFER_NOT_SAY = 'prefer_not_say', 'Prefer not to say'

    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type            = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials      = models.CharField(max_length=4, blank=True)
    competency_score     = models.PositiveSmallIntegerField(default=0)
    subject_area         = models.CharField(max_length=20, choices=SubjectArea.choices, blank=True)
    teaching_level       = models.CharField(max_length=20, choices=TeachingLevel.choices, blank=True)
    goals                = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    preferred_pillars    = models.JSONField(default=list, blank=True)
    learning_style       = models.CharField(
        max_length=20, choices=LearningStyle.choices, blank=True,
    )
    school               = models.CharField(max_length=200, blank=True)
    phone                = models.CharField(max_length=30, blank=True)
    location             = models.CharField(max_length=200, blank=True)
    weekly_learning_goal = models.CharField(max_length=10, choices=WeeklyGoal.choices, blank=True)
    email_notifications  = models.BooleanField(default=True)
    progress_reminders   = models.BooleanField(default=True)
    profile_public       = models.BooleanField(default=False)
    share_progress       = models.BooleanField(default=False)
    gender               = models.CharField(
        max_length=20, choices=Gender.choices, blank=True,
    )
    country              = models.CharField(max_length=2, blank=True)
    avatar               = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'
