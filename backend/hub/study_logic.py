"""Helpers for the adaptive-vs-fixed comparison study."""
import random

from hub.models import StudyConfig, StudyParticipant


def active_group(user):
    """The study group ('adaptive'|'fixed') for an enrolled participant while the
    study is running, else None. Used to branch the learner experience."""
    if not StudyConfig.get().enabled:
        return None
    p = StudyParticipant.objects.filter(user=user, in_study=True).first()
    return p.group if p else None


def assign_group():
    """Balanced 50/50 allocation across currently-enrolled participants."""
    adaptive = StudyParticipant.objects.filter(
        in_study=True, group=StudyParticipant.Group.ADAPTIVE).count()
    fixed = StudyParticipant.objects.filter(
        in_study=True, group=StudyParticipant.Group.FIXED).count()
    if adaptive < fixed:
        return StudyParticipant.Group.ADAPTIVE
    if fixed < adaptive:
        return StudyParticipant.Group.FIXED
    return random.choice([StudyParticipant.Group.ADAPTIVE, StudyParticipant.Group.FIXED])
