from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    class UserType(models.TextChoices):
        TEACHER = 'teacher', 'Teacher'
        CONTENT_CREATOR = 'content_creator', 'Content Creator'
        ADMIN = 'admin', 'Admin'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.TEACHER)
    avatar_initials = models.CharField(max_length=4, blank=True)

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_user_type_display()})'
