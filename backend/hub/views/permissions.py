from rest_framework.permissions import BasePermission

from hub.models import UserProfile

# Roles are hierarchical for content work: AIDEA partners and admins are also
# content creators (admins additionally manage the platform).
CONTENT_CREATOR_ROLES = {
    UserProfile.UserType.CONTENT_CREATOR,
    UserProfile.UserType.AIDEA_PARTNER,
    UserProfile.UserType.ADMIN,
}


class IsContentCreator(BasePermission):
    def has_permission(self, request, view):
        profile = getattr(request.user, 'profile', None)
        return (
            request.user.is_authenticated
            and profile is not None
            and profile.user_type in CONTENT_CREATOR_ROLES
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.TEACHER
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.ADMIN
        )


class IsReviewer(BasePermission):
    """Course creators, AIDEA Partners, and admins may review assignment submissions."""

    def has_permission(self, request, view):
        profile = getattr(request.user, 'profile', None)
        return (
            request.user.is_authenticated
            and profile is not None
            and profile.user_type in (
                UserProfile.UserType.CONTENT_CREATOR,
                UserProfile.UserType.AIDEA_PARTNER,
                UserProfile.UserType.ADMIN,
            )
        )


def _is_admin(user):
    profile = getattr(user, 'profile', None)
    return profile is not None and profile.user_type == UserProfile.UserType.ADMIN


def _has_collaborator_role(user, course, role):
    from hub.models import CourseCollaborator
    return CourseCollaborator.objects.filter(course=course, user=user, role=role).exists()


def can_manage_course(user, course):
    """Owner-only actions: delete the course, reassign authorship, and manage its
    collaborators. Only the author or an admin."""
    return course.created_by_id == user.id or _is_admin(user)


def can_edit_course(user, course):
    """Who may edit or publish a course (draft or published) and its modules and
    lessons: the author, an admin, or a co-editor collaborator. Translators and
    other content creators / partners cannot touch the source content."""
    from hub.models import CourseCollaborator
    return (
        course.created_by_id == user.id
        or _is_admin(user)
        or _has_collaborator_role(user, course, CourseCollaborator.Role.CO_EDITOR)
    )


def can_translate_course(user, course):
    """Who may add and edit translations: everyone who can edit the source, plus
    translators assigned to this course."""
    from hub.models import CourseCollaborator
    return (
        can_edit_course(user, course)
        or _has_collaborator_role(user, course, CourseCollaborator.Role.TRANSLATOR)
    )


def can_review_translation(user, course):
    """Who may sign off a translation as human-reviewed: admins and AIDEA
    partners (any course), plus anyone who may translate this course (author,
    co-editors and its translators)."""
    profile = getattr(user, 'profile', None)
    if profile is None:
        return False
    if profile.user_type in (UserProfile.UserType.ADMIN, UserProfile.UserType.AIDEA_PARTNER):
        return True
    return can_translate_course(user, course)
