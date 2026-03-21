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

    title              = models.CharField(max_length=200)
    description        = models.TextField(blank=True)
    pillar             = models.ForeignKey(LearningPillar, on_delete=models.PROTECT, related_name='courses')
    level              = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    duration_hours     = models.PositiveSmallIntegerField(default=0)
    learning_outcomes  = models.JSONField(default=list, blank=True)
    is_published       = models.BooleanField(default=False)
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


class Lesson(models.Model):
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
    # quiz_data structure (only used when lesson_type='quiz'):
    # [{"question": str, "options": [{"text": str, "is_correct": bool}]}]
    quiz_data        = models.JSONField(default=list, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=0)
    order            = models.PositiveSmallIntegerField(default=0)
    is_required      = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.module.title} — {self.title}'
