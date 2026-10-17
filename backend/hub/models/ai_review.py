"""AI assignment reviewer — see docs/superpowers/specs/2026-10-16-ai-assignment-review-design.md."""
from django.contrib.auth.models import User
from django.db import models


class AIReviewSettings(models.Model):
    """Platform-wide switch and thresholds (singleton, edited in Django admin)."""
    enabled              = models.BooleanField(default=False)
    model_name           = models.CharField(max_length=100, default='qwen2.5vl:32b')
    confidence_threshold = models.FloatField(default=0.8)
    spot_check_rate      = models.FloatField(default=0.1)
    unlock_min_reviews   = models.PositiveIntegerField(default=30)
    # Auto-approve unlocks when the 95% Wilson lower bound of agreement on the
    # AI's approvals reaches this (0.9 needs at least 35 agreeing approvals).
    unlock_min_lower_bound = models.FloatField(default=0.9)

    class Meta:
        verbose_name = verbose_name_plural = 'AI review settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return 'AI review settings'


class AssignmentReviewConfig(models.Model):
    """One assignment's AI review set-up: rubric, examples policy, visibility."""
    resource              = models.OneToOneField('hub.Resource', on_delete=models.CASCADE, related_name='ai_review_config')
    enabled               = models.BooleanField(default=False)
    criteria              = models.JSONField(default=list, blank=True)   # [{id, name, met, required}]
    rubric_approved       = models.BooleanField(default=False)
    criteria_translations = models.JSONField(default=dict, blank=True)   # {lang: {criterion id: name}}
    learner_visible       = models.BooleanField(default=False)
    auto_approve          = models.BooleanField(default=False)
    duplicate_check       = models.BooleanField(default=True)
    updated_at            = models.DateTimeField(auto_now=True)

    def is_ready(self):
        return self.enabled and self.rubric_approved and bool(self.criteria)

    def __str__(self):
        return f'AI review config for resource {self.resource_id}'


class ReviewExample(models.Model):
    """A sample submission with its correct verdict, shown to the model."""
    resource          = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='ai_review_examples')
    text              = models.TextField(blank=True)
    image_path        = models.CharField(max_length=500, blank=True)  # reserved: image examples come later
    verdict           = models.CharField(max_length=20, choices=[('approve', 'Approve'), ('changes_requested', 'Changes requested')])
    reason            = models.TextField(blank=True)
    source_submission = models.ForeignKey('hub.AssignmentSubmission', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class AIReview(models.Model):
    """One AI review of one submission version."""
    class Status(models.TextChoices):
        QUEUED  = 'queued',  'Queued'
        RUNNING = 'running', 'Running'
        DONE    = 'done',    'Done'
        FAILED  = 'failed',  'Failed'

    class Verdict(models.TextChoices):
        APPROVE = 'approve',           'Approve'
        CHANGES = 'changes_requested', 'Changes requested'
        UNSURE  = 'unsure',            'Unsure'

    DISAGREEMENT_REASONS = ('missed_evidence', 'too_strict', 'too_lenient', 'misread_image', 'other')

    submission          = models.ForeignKey('hub.AssignmentSubmission', on_delete=models.CASCADE, related_name='ai_reviews')
    status              = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    model_name          = models.CharField(max_length=100, blank=True)
    prompt_version      = models.CharField(max_length=40, blank=True)
    rubric              = models.JSONField(default=list, blank=True)        # snapshot of the criteria used
    checks              = models.JSONField(default=dict, blank=True)        # {fingerprints: [...], duplicates: [...]}
    criteria_results    = models.JSONField(default=list, blank=True)        # [{id, status, reason}]
    verdict             = models.CharField(max_length=20, choices=Verdict.choices, blank=True)
    confidence          = models.FloatField(null=True, blank=True)
    learner_feedback    = models.TextField(blank=True)
    reviewer_notes      = models.TextField(blank=True)
    error               = models.TextField(blank=True)
    attempts            = models.PositiveSmallIntegerField(default=0)
    created_at          = models.DateTimeField(auto_now_add=True)
    finished_at         = models.DateTimeField(null=True, blank=True)
    duration_s          = models.FloatField(null=True, blank=True)
    auto_approved       = models.BooleanField(default=False)
    spot_check          = models.BooleanField(default=False)
    human_verdict       = models.CharField(max_length=20, blank=True)
    agreed              = models.BooleanField(null=True, blank=True)
    disagreement_reason = models.CharField(max_length=20, blank=True)
    feedback_used       = models.BooleanField(default=False)            # reviewer started from the AI's feedback
    feedback_similarity = models.FloatField(null=True, blank=True)     # 1.0 = sent unchanged

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['submission', 'status'])]

    @property
    def flagged(self):
        return bool((self.checks or {}).get('duplicates'))

    @property
    def resource(self):
        return self.submission.resource

    def __str__(self):
        return f'AI review {self.id} of submission {self.submission_id} ({self.status})'
