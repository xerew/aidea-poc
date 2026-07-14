from rest_framework.permissions import BasePermission

from hub.models import UserProfile


class IsContentCreator(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.CONTENT_CREATOR
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


def can_edit_published(user, course):
    """Published courses may only be edited by their author or an admin."""
    profile = getattr(user, 'profile', None)
    is_admin = profile is not None and profile.user_type == UserProfile.UserType.ADMIN
    return course.created_by_id == user.id or is_admin
