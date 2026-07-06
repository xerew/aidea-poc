from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.serializers.profile import (
    ProfilePersonalInfoSerializer,
    ProfilePreferencesSerializer,
    ProfileSettingsSerializer,
)
from hub.tasks import compute_user_recommendations
from hub.views.permissions import IsTeacher


class ProfilePreferencesView(APIView):
    permission_classes = [IsTeacher]

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


def _password_errors(password: str) -> list[str]:
    import re
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if len(password) > 128:
        errors.append('no more than 128 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        errors.append('at least one lowercase letter')
    if not re.search(r'\d', password):
        errors.append('at least one number')
    if not re.search(r'[^A-Za-z0-9]', password):
        errors.append('at least one special character (!@#$%…)')
    return errors


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
