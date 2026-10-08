"""Uploaded H5P activities — see docs/superpowers/specs/2026-10-08-h5p-activities-design.md.

One H5PPackage per H5P resource × language ('' = the main file). The archive
is unpacked under MEDIA_ROOT/<folder> and played by h5p-standalone in a
sandboxed frame. Re-uploading bumps `version`; old folders are kept because
copied modules and earlier attempts may still point at them."""
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class H5PPackage(models.Model):
    resource     = models.ForeignKey('hub.Resource', on_delete=models.CASCADE, related_name='h5p_packages')
    language     = models.CharField(max_length=8, blank=True)  # '' = main file
    file         = models.FileField(upload_to='h5p_uploads/')
    folder       = models.CharField(max_length=100)             # e.g. 'h5p/3f2a…' under MEDIA_ROOT
    title        = models.CharField(max_length=255, blank=True)
    main_library = models.CharField(max_length=100)
    size_bytes   = models.PositiveBigIntegerField(default=0)
    version      = models.PositiveIntegerField(default=1)
    uploaded_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    uploaded_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('resource', 'language')
        ordering = ['language']

    def __str__(self):
        return f'{self.main_library} for resource {self.resource_id} [{self.language or "main"}]'

    @property
    def media_path(self):
        """Site-relative URL of the unpacked folder."""
        return f'{settings.MEDIA_URL}{self.folder}'
