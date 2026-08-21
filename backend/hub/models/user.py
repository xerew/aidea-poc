from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER         = 'teacher',         'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN           = 'admin',           'Admin'
        AIDEA_PARTNER   = 'aidea_partner',   'AIDEA Partner'

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

    class Language(models.TextChoices):
        EN = 'en', 'English'
        EL = 'el', 'Ελληνικά'
        FR = 'fr', 'Français'
        ES = 'es', 'Español'
        IT = 'it', 'Italiano'
        FI = 'fi', 'Suomi'
        SV = 'sv', 'Svenska'
        NO = 'no', 'Norsk'
        DE = 'de', 'Deutsch'

    user                 = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type            = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials      = models.CharField(max_length=4, blank=True)
    email_verified       = models.BooleanField(default=False)
    competency_score     = models.PositiveSmallIntegerField(default=0)
    subject              = models.ForeignKey(
        'hub.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers',
    )
    teaching_level       = models.CharField(max_length=20, choices=TeachingLevel.choices, blank=True)
    goals                = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    # AI self-efficacy assessment: saved incrementally so it can be paused and
    # resumed. {question_id: 1-5}. completed_at is set once every active
    # question has an answer.
    self_efficacy_answers      = models.JSONField(default=dict, blank=True)
    self_efficacy_completed_at = models.DateTimeField(null=True, blank=True)
    # A retake in progress writes here (not to the fields above), so the already
    # completed results stay intact until the retake is actually finished.
    self_efficacy_draft        = models.JSONField(default=dict, blank=True)
    self_efficacy_retaking     = models.BooleanField(default=False)
    preferred_pillars    = models.JSONField(default=list, blank=True)
    learning_style       = models.CharField(
        max_length=20, choices=LearningStyle.choices, blank=True,
    )
    school               = models.CharField(max_length=200, blank=True)
    phone                = models.CharField(max_length=30, blank=True)
    location             = models.CharField(max_length=200, blank=True)
    bio                  = models.TextField(blank=True)
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
    language             = models.CharField(max_length=5, choices=Language.choices, default=Language.EN)
    # When the user accepted the Terms of Service and Privacy Policy (at registration).
    accepted_terms_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'
