from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, CourseCollaborator, UserProfile

from .permissions import (
    CONTENT_CREATOR_ROLES,
    IsContentCreator,
    can_manage_course,
    can_translate_course,
)

# Roles eligible to be added as collaborators (admins already edit everything).
# Admins count as AIDEA partners, so they can be added too.
_CANDIDATE_ROLES = [
    UserProfile.UserType.CONTENT_CREATOR,
    UserProfile.UserType.AIDEA_PARTNER,
    UserProfile.UserType.ADMIN,
]


def _serialize(collab):
    u = collab.user
    return {
        'user_id': u.id,
        'username': u.username,
        'name': u.get_full_name() or u.username,
        'role': collab.role,
        'role_display': collab.get_role_display(),
    }


class AuthoringCourseCollaboratorsView(APIView):
    """GET  → collaborators on a course.
       POST {user_id, role} → add or update a collaborator (owner/admin only)."""
    permission_classes = [IsContentCreator]

    def get(self, request, pk):
        course = Course.objects.filter(pk=pk).first()
        if course is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_translate_course(request.user, course):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)
        collabs = course.collaborators.select_related('user').all()
        return Response([_serialize(c) for c in collabs])

    def post(self, request, pk):
        course = Course.objects.filter(pk=pk).first()
        if course is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_manage_course(request.user, course):
            return Response({'detail': 'Only the author can manage collaborators.'},
                            status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role')
        if role not in CourseCollaborator.Role.values:
            return Response({'detail': 'Invalid role.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.select_related('profile').get(pk=request.data.get('user_id'))
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Unknown user.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.id == course.created_by_id:
            return Response({'detail': 'This user is already the author of the course.'},
                            status=status.HTTP_400_BAD_REQUEST)

        profile = getattr(user, 'profile', None)
        if profile is None or profile.user_type not in CONTENT_CREATOR_ROLES:
            return Response(
                {'detail': 'Collaborators must be content creators, AIDEA partners or admins.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collab, _ = CourseCollaborator.objects.update_or_create(
            course=course, user=user,
            defaults={'role': role, 'added_by': request.user},
        )
        return Response(_serialize(collab), status=status.HTTP_201_CREATED)


class AuthoringCollaboratorCandidatesView(APIView):
    """GET ?q= → content creators, AIDEA partners and admins who can be added
    as collaborators (for the add-collaborator picker)."""
    permission_classes = [IsContentCreator]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        users = User.objects.select_related('profile').filter(profile__user_type__in=_CANDIDATE_ROLES)
        if q:
            users = users.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q),
            )
        users = users.order_by('first_name', 'username')[:20]
        return Response([
            {
                'id': u.id,
                'username': u.username,
                'name': u.get_full_name() or u.username,
                'user_type': u.profile.user_type,
            }
            for u in users
        ])


class AuthoringCourseCollaboratorDetailView(APIView):
    """DELETE → remove a collaborator (owner/admin only)."""
    permission_classes = [IsContentCreator]

    def delete(self, request, pk, user_id):
        course = Course.objects.filter(pk=pk).first()
        if course is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not can_manage_course(request.user, course):
            return Response({'detail': 'Only the author can manage collaborators.'},
                            status=status.HTTP_403_FORBIDDEN)
        CourseCollaborator.objects.filter(course=course, user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
