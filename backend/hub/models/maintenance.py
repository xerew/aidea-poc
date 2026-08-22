from django.db import models


class MaintenanceNotice(models.Model):
    """Singleton: an admin-scheduled maintenance/downtime banner shown to users
    (e.g. "the platform will be unavailable from … to … for an update")."""
    enabled = models.BooleanField(default=False)
    message = models.TextField(blank=True)          # optional reason
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_active(self, now):
        """Show the banner while enabled and the window hasn't fully passed
        (so it informs before and during, and auto-hides afterwards)."""
        return self.enabled and (self.ends_at is None or now < self.ends_at)

    def __str__(self):
        return 'Maintenance notice'
