from django.contrib.auth.models import User
from django.db import models


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

    class ContentFormat(models.TextChoices):
        VIDEO       = 'video',       'Video'
        TEXT        = 'text',        'Text'
        VISUAL      = 'visual',      'Visual'
        INTERACTIVE = 'interactive', 'Interactive'
        MIXED       = 'mixed',       'Mixed'

    title              = models.CharField(max_length=200)
    description        = models.TextField(blank=True)
    pillar             = models.ForeignKey(LearningPillar, on_delete=models.PROTECT, related_name='courses')
    level              = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    duration_hours     = models.PositiveSmallIntegerField(default=0)
    learning_outcomes  = models.JSONField(default=list, blank=True)
    is_published       = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    created_by         = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_courses',
    )
    content_format     = models.CharField(
        max_length=20, choices=ContentFormat.choices, default=ContentFormat.MIXED,
    )
    subjects           = models.ManyToManyField('hub.Subject', blank=True, related_name='courses')
    source_language     = models.CharField(max_length=5, default='en')
    # translations: {lang_code: {"title": str, "description": str, ...}}
    translations        = models.JSONField(default=dict, blank=True)
    # translation_status: {lang_code: "pending"|"in_progress"|"done"|"failed"}
    translation_status  = models.JSONField(default=dict, blank=True)

    # Course-proposal fields. `pillar` stays the primary Academy Pillar (ordering,
    # colour, home-page grouping); `additional_pillars` are the other axes the
    # course also serves, explained in `cross_axis_relevance`.
    additional_pillars   = models.ManyToManyField(
        LearningPillar, blank=True, related_name='secondary_courses',
    )
    cross_axis_relevance = models.TextField(blank=True)
    # Lists of AUDIENCE_CHOICES / EDUCATIONAL_LEVEL_CHOICES values, plus free text.
    target_audience          = models.JSONField(default=list, blank=True)
    target_audience_other    = models.CharField(max_length=200, blank=True)
    educational_levels       = models.JSONField(default=list, blank=True)
    educational_level_other  = models.CharField(max_length=200, blank=True)
    prior_knowledge          = models.TextField(blank=True)

    AUDIENCE_CHOICES = ['teachers', 'school_leaders']
    EDUCATIONAL_LEVEL_CHOICES = ['primary', 'lower_secondary', 'upper_secondary', 'cross_level']

    class Meta:
        ordering = ['pillar', 'title']

    def __str__(self):
        return self.title


class CourseCollaborator(models.Model):
    """Grants a content creator / AIDEA partner rights on a course they did not
    author: a co-editor (full editing, like the author) or a translator (may
    only add and edit translations, not the source content)."""
    class Role(models.TextChoices):
        CO_EDITOR  = 'co_editor',  'Co-editor'
        TRANSLATOR = 'translator', 'Translator'

    course     = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='collaborators')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_collaborations')
    role       = models.CharField(max_length=20, choices=Role.choices)
    added_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'user')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} — {self.get_role_display()} on {self.course.title}'


class Resource(models.Model):
    """One content block inside an Activity. An activity owns an ordered list of
    resources, each of a single type. Payload lives in typed columns; only the
    ones relevant to `type` are used."""
    class Type(models.TextChoices):
        TEXT       = 'text',       'Text'
        VIDEO      = 'video',      'Video'
        IMAGE      = 'image',      'Image'
        PDF        = 'pdf',        'PDF'
        QUIZ       = 'quiz',       'Quiz'
        ASSIGNMENT = 'assignment', 'Assignment'
        H5P        = 'h5p',        'H5P activity'

    activity     = models.ForeignKey('hub.Activity', on_delete=models.CASCADE, related_name='resources')
    type         = models.CharField(max_length=20, choices=Type.choices)
    order        = models.PositiveSmallIntegerField(default=0)
    is_required  = models.BooleanField(default=True)
    title        = models.CharField(max_length=200, blank=True)
    content      = models.TextField(blank=True)                 # text
    url          = models.CharField(max_length=500, blank=True)  # video/image/pdf
    caption      = models.CharField(max_length=300, blank=True)
    quiz_data    = models.JSONField(default=list, blank=True)    # quiz
    instructions = models.TextField(blank=True)                  # assignment
    translations = models.JSONField(default=dict, blank=True)
    # h5p: learners mark it done themselves (types that never report finishing).
    h5p_self_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.activity.title} — {self.get_type_display()}'


class Module(models.Model):
    title            = models.CharField(max_length=200)
    description      = models.TextField(blank=True)
    course           = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order            = models.PositiveSmallIntegerField(default=0)
    duration_minutes = models.PositiveSmallIntegerField(default=0)
    # Stub toggle: per-module LLM assignment reviewer ("later turned on")
    llm_review_enabled = models.BooleanField(default=False)
    # translations: {lang_code: {"title": str, "description": str}}
    translations     = models.JSONField(default=dict, blank=True)
    # Indices into course.learning_outcomes this module addresses.
    related_outcomes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class Activity(models.Model):
    class LessonType(models.TextChoices):
        TEXT       = 'text',       'Text'
        VIDEO      = 'video',      'Video'
        IMAGE      = 'image',      'Image'
        QUIZ       = 'quiz',       'Quiz'
        PDF        = 'pdf',        'PDF'
        ASSIGNMENT = 'assignment', 'Assignment'

    module           = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title            = models.CharField(max_length=200)
    description      = models.TextField(blank=True)
    lesson_type      = models.CharField(
        max_length=20, choices=LessonType.choices, default=LessonType.TEXT,
    )
    content          = models.TextField(blank=True)
    # media_items: ordered attachments shown after the text body.
    # [{"type": "image"|"video"|"pdf", "url": str, "caption": str}]
    media_items      = models.JSONField(default=list, blank=True)
    # quiz_data structure (only used when lesson_type='quiz'):
    # [{"question": str, "options": [{"text": str, "is_correct": bool}]}]
    quiz_data        = models.JSONField(default=list, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=0)
    order            = models.PositiveSmallIntegerField(default=0)
    is_required      = models.BooleanField(default=True)
    # translations: {lang_code: {"title": str, "description": str, "content": str}}
    translations     = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.module.title} — {self.title}'
