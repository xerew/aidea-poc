"""Every change to a teacher's AI competency score, with its reason — see
docs/superpowers/specs/2026-10-21-competency-performance-design.md."""
from django.contrib.auth.models import User
from django.db import models


class CompetencyChange(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='competency_changes')
    course     = models.ForeignKey('hub.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    old_score  = models.PositiveSmallIntegerField()
    new_score  = models.PositiveSmallIntegerField()
    delta      = models.SmallIntegerField()                 # new − old (after clamping to 0..6)
    # {rule: performance|completion|idle, performance, passed, course_level,
    #  teacher_level, gap, base_delta, slow_penalty} — see hub/competency.py
    reason     = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user} {self.old_score}→{self.new_score}'
