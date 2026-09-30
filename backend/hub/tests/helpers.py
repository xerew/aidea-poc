from hub.completion import ensure_resources
from hub.content_migration_logic import migrate_progress_row
from hub.models import LessonProgress, Resource, ResourceProgress


def complete_activity(user, lesson, **fields):
    """Record a completed activity the way migrated data looks: a legacy
    LessonProgress row mirrored onto every resource of the activity."""
    ensure_resources(lesson)
    lp = LessonProgress.objects.create(user=user, lesson=lesson, **fields)
    migrate_progress_row(lp, Resource, ResourceProgress)
    return lp
