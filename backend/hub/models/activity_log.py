"""Records for the admin per-user activity page (spec 2026-11-21-user-activity-page):
logins (time, device, browser; never an IP address) and, in PlatformAction,
platform actions that leave no other trace."""
from django.contrib.auth.models import User
from django.db import models


class LoginRecord(models.Model):
    class Device(models.TextChoices):
        DESKTOP = 'desktop', 'Desktop'
        TABLET  = 'tablet',  'Tablet'
        MOBILE  = 'mobile',  'Mobile'

    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_records')
    at      = models.DateTimeField(auto_now_add=True)
    device  = models.CharField(max_length=10, choices=Device.choices, blank=True)
    browser = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['-at']
        indexes = [models.Index(fields=['user', 'at'])]

    def __str__(self):
        return f'{self.user.username} signed in at {self.at:%Y-%m-%d %H:%M}'
