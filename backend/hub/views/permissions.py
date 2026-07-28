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


def can_edit_published(user, course):
    """Published courses may be edited by their author, or by an admin (who
    manages everything). Content creators and partners can still edit their own
    published courses via the author check."""
    profile = getattr(user, 'profile', None)
    is_admin = profile is not None and profile.user_type == UserProfile.UserType.ADMIN
    return course.created_by_id == user.id or is_admin


def can_review_translation(user, course):
    """Who may sign off a translation as human-reviewed: the course author,
    admins, and AIDEA partners."""
    profile = getattr(user, 'profile', None)
    if profile is None:
        return False
    if profile.user_type in (UserProfile.UserType.ADMIN, UserProfile.UserType.AIDEA_PARTNER):
        return True
    return course.created_by_id == user.id
