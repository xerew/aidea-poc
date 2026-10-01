from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from hub.models import Feedback, UserProfile
from hub.models.content import Course


@receiver(post_save, sender=Course)
def course_published_handler(sender, instance, created, **kwargs):
    if instance.is_published:
        from hub.tasks import compute_course_embeddings
        compute_course_embeddings.delay(instance.pk)


@receiver(pre_save, sender=UserProfile)
def remember_previous_role(sender, instance, **kwargs):
    instance._previous_user_type = (
        UserProfile.objects.filter(pk=instance.pk).values_list('user_type', flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=UserProfile)
def move_feedback_with_role(sender, instance, created, **kwargs):
    """When someone becomes (or stops being) an AIDEA partner, their earlier
    feedback moves to the matching stream, whatever screen changed the role."""
    previous = getattr(instance, '_previous_user_type', None)
    if created or previous == instance.user_type:
        return
    Feedback.objects.filter(user_id=instance.user_id).update(
        stream=Feedback.stream_for_role(instance.user_type),
    )
