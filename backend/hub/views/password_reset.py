import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    """POST /api/auth/password-reset/ {email} — email a reset link.

    Always returns the same response so it can't be used to probe which
    email addresses have accounts.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get('email', '')).strip()
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user and user.email:
                self._send(user)
        return Response({'detail': 'If that email is registered, a reset link has been sent.'})

    def _send(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f'{settings.FRONTEND_BASE_URL}/reset-password/{uid}/{token}'
        name = user.get_full_name() or user.username
        text = (
            f'Hello {name},\n\n'
            'We received a request to reset your AIDEA password. '
            'Open the link below to choose a new one:\n\n'
            f'{link}\n\n'
            "If you didn't request this, you can safely ignore this email — "
            'your password will stay the same.\n\n'
            'The AIDEA team'
        )
        html = (
            f'<p>Hello {name},</p>'
            '<p>We received a request to reset your AIDEA password. '
            'Click the button below to choose a new one:</p>'
            f'<p><a href="{link}" style="display:inline-block;padding:10px 18px;'
            'background:#1d4ed8;color:#fff;text-decoration:none;border-radius:6px">'
            'Reset password</a></p>'
            f'<p>Or paste this link into your browser:<br><a href="{link}">{link}</a></p>'
            "<p>If you didn't request this, you can safely ignore this email.</p>"
            '<p>— The AIDEA team</p>'
        )
        try:
            send_mail(
                subject='Reset your AIDEA password',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html,
            )
        except Exception:  # noqa: BLE001 — never leak SMTP errors to the caller
            logger.exception('Failed to send password-reset email to %s', user.email)


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/ {uid, token, new_password}."""
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password') or ''

        user = None
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {'detail': 'This reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except ValidationError as exc:
            return Response({'detail': ' '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Your password has been reset. You can now sign in.'})
