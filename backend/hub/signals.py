from django.db.models.signals import post_save
from django.dispatch import receiver

from hub.models.content import Course


@receiver(post_save, sender=Course)
def course_published_handler(sender, instance, created, **kwargs):
    if instance.is_published:
        from hub.tasks import compute_course_embeddings
        compute_course_embeddings.delay(instance.pk)
