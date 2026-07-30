from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, Enrollment
from hub.views.onboarding import get_competency_level

CREATOR_ROLES = ('content_creator', 'aidea_partner')


class PublicProfileView(APIView):
    """GET /api/users/<pk>/profile/ — another user's public profile.

    Always returns identity (name/avatar/role) so entry points can label the
    link; the rest is included only when the user enabled `profile_public`.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.select_related('profile', 'profile__subject').get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile = getattr(user, 'profile', None)
        if profile is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        avatar_url = None
        if profile.avatar:
            avatar_url = request.build_absolute_uri(profile.avatar.url)

        data = {
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'user_type': profile.user_type,
            'avatar_url': avatar_url,
            'avatar_initials': profile.avatar_initials,
            'gender': profile.gender,          # for the gender-based avatar fallback
            'is_public': profile.profile_public,
        }
        if not profile.profile_public:
            return Response(data)

        data.update({
            'bio': profile.bio,
            'subject_name': profile.subject.name if profile.subject else '',
            'subject_slug': profile.subject.slug if profile.subject else '',
            'teaching_level': profile.get_teaching_level_display() if profile.teaching_level else '',
            'school': profile.school,
            'country': profile.country,
            'member_since': user.date_joined,
        })

        if profile.user_type == 'teacher':
            data['competency'] = {
                'level': get_competency_level(profile.competency_score),
                'score': profile.competency_score,
            }
            if profile.share_progress:
                enrollments = list(Enrollment.objects.filter(user=user))
                data['progress'] = {
                    'completed': sum(1 for e in enrollments if e.progress_pct == 100),
                    'in_progress': sum(1 for e in enrollments if 0 < e.progress_pct < 100),
                }

        if profile.user_type in CREATOR_ROLES:
            courses = (
                Course.objects
                .filter(created_by=user, is_published=True)
                .select_related('pillar')
                .order_by('title')
            )
            data['authored_courses'] = [
                {'id': c.id, 'title': c.title, 'pillar_name': c.pillar.name} for c in courses
            ]

        return Response(data)
