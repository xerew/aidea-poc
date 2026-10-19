"""Uploaded PowerPoint decks for presentation resources — see
docs/superpowers/specs/2026-10-19-presentation-resource-design.md.

One PresentationFile per presentation resource × language ('' = the main
deck), played in Microsoft's Office viewer, which fetches the file by its
public (but unguessable) URL. Each file belongs to exactly one resource —
copied modules get their own copy — so replacing or removing deletes it."""
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def presentation_upload_to(instance, filename):
    return f'presentations/{instance.resource_id}/{uuid.uuid4().hex}.pptx'


class PresentationFile(models.Model):
    resource    = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='presentation_files')
    language    = models.CharField(max_length=8, blank=True)  # '' = main deck
    file        = models.FileField(upload_to=presentation_upload_to, max_length=255)
    title       = models.CharField(max_length=255, blank=True)
    slide_count = models.PositiveIntegerField(default=0)
    size_bytes  = models.PositiveBigIntegerField(default=0)
    version     = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('resource', 'language')
        ordering = ['language']

    def __str__(self):
        return f'Deck for resource {self.resource_id} [{self.language or "main"}]'

    @property
    def over_viewer_limit(self):
        return self.size_bytes > settings.PRESENTATION_VIEWER_LIMIT_MB * 1024 * 1024

    @property
    def media_path(self):
        """Site-relative URL of the file."""
        return f'{settings.MEDIA_URL}{self.file.name}'


@receiver(post_delete, sender=PresentationFile)
def _delete_deck_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
