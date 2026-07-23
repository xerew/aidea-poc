from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import UserProfile
from hub.serializers.auth import _PASSWORD_RULES, UserSerializer
from hub.serializers.profile import (
    ProfilePersonalInfoSerializer,
    ProfilePreferencesSerializer,
    ProfileSettingsSerializer,
)
from hub.tasks import compute_user_recommendations


def _regenerate_pathway(user):
    """Re-personalise an onboarded teacher's pathway after a preference or
    subject change. No-op for users who haven't onboarded (no pathway yet)."""
    from hub.models.pathway import UserLearningPath
    from hub.pathway_gen import generate_pathway
    try:
        user_path = UserLearningPath.objects.get(user=user)
    except UserLearningPath.DoesNotExist:
        return
    user_path.course_ids = generate_pathway(user)
    user_path.save(update_fields=['course_ids'])


class ProfilePreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfilePreferencesSerializer(request.user.profile)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfilePreferencesSerializer(
            request.user.profile, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        compute_user_recommendations.delay(request.user.id)
        _regenerate_pathway(request.user)
        return Response(serializer.data)


class ProfilePersonalInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfilePersonalInfoSerializer(request.user.profile)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfilePersonalInfoSerializer(
            request.user.profile, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user.profile, serializer.validated_data)
        # Subject feeds the pathway ranking, so a change re-personalises it.
        _regenerate_pathway(request.user)
        return Response(ProfilePersonalInfoSerializer(request.user.profile).data)


class ProfileSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSettingsSerializer(request.user.profile)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileSettingsSerializer(
            request.user.profile, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        profile = request.user.profile
        if profile.avatar:
            profile.avatar.delete(save=False)
        profile.avatar = file
        profile.save(update_fields=['avatar'])
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def delete(self, request):
        profile = request.user.profile
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.save(update_fields=['avatar'])
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ProfileLanguageView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        language = request.data.get('language')
        valid = {c[0] for c in UserProfile.Language.choices}
        if language not in valid:
            return Response({'error': 'Invalid language.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.profile.language = language
        request.user.profile.save(update_fields=['language'])
        return Response({'language': language})


def _password_errors(password: str) -> list[str]:
    return [msg for check, msg in _PASSWORD_RULES if not check(password)]


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old_password and new_password are required.'}, status=400,
            )
        if not request.user.check_password(old_password):
            return Response({'error': 'Current password is incorrect.'}, status=400)
        errors = _password_errors(new_password)
        if errors:
            return Response(
                {'error': f"Password must have: {', '.join(errors)}."}, status=400,
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({'message': 'Password changed successfully.'})
