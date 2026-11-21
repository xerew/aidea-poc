"""What happens when courses are published or unpublished (in the app or Django admin)."""


def course_publication_changed(course_ids, published, user):
    """List the change for the next admin-triggered pathway rebuild and, once
    saved, refresh the courses' embeddings and everyone's recommendations.
    Pathways themselves change only when an admin rebuilds them."""
    if not course_ids:
        return
    from django.db import transaction

    from hub.models import Course, PathwayCourseChange
    from hub.tasks import refresh_after_publish

    change = PathwayCourseChange.Change.PUBLISHED if published else PathwayCourseChange.Change.UNPUBLISHED
    by = user if getattr(user, 'is_authenticated', False) else None
    PathwayCourseChange.objects.bulk_create([
        PathwayCourseChange(course=course, course_title=course.title, change=change, changed_by=by)
        for course in Course.objects.filter(pk__in=course_ids)
    ])
    ids = list(course_ids)
    transaction.on_commit(lambda: refresh_after_publish.delay(ids))
