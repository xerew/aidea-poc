from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from hub.emails import (
    read_verify_token,
    send_verification_email,
    send_welcome_email,
)
from hub.serializers import AideaTokenObtainPairSerializer, RegisterSerializer, UserSerializer
from hub.throttling import LoginIPThrottle, LoginUserThrottle


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AideaTokenObtainPairSerializer
    # Brute-force protection: cap attempts per account and per source IP.
    throttle_classes = [LoginUserThrottle, LoginIPThrottle]


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out.'})


class MeView(APIView):
    """GET /api/auth/me/ — current user with fresh profile (role) data."""

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Best-effort welcome + email-verification (never blocks registration).
        send_welcome_email(user)
        send_verification_email(user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UserSerializer(user).data,
        }, status=201)


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/ {token} — mark the account's email verified."""
    permission_classes = [AllowAny]

    def post(self, request):
        uid = read_verify_token(str(request.data.get('token', '')))
        if uid is None:
            return Response(
                {'detail': 'This confirmation link is invalid or has expired.'},
                status=400,
            )
        try:
            user = User.objects.select_related('profile').get(pk=uid)
        except User.DoesNotExist:
            return Response({'detail': 'Account not found.'}, status=400)
        if not user.profile.email_verified:
            user.profile.email_verified = True
            user.profile.save(update_fields=['email_verified'])
        return Response({'detail': 'Your email is confirmed.', 'verified': True})


class ResendVerificationView(APIView):
    """POST /api/auth/verify-email/resend/ — re-send the confirmation email."""

    def post(self, request):
        if request.user.profile.email_verified:
            return Response({'detail': 'Your email is already confirmed.'})
        send_verification_email(request.user)
        return Response({'detail': 'Confirmation email sent.'})
