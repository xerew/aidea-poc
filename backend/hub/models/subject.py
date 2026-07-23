from django.db import models


class Subject(models.Model):
    """Teaching subject, shared by teacher profiles (single) and courses (many).

    Admin-editable so the taxonomy can grow without a code change.
    """

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
