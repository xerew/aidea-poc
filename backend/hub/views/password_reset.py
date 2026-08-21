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

from hub.throttling import PasswordResetEmailThrottle, PasswordResetIPThrottle

logger = logging.getLogger(__name__)


def _reset_email_html(name, link):
    base = settings.FRONTEND_BASE_URL
    logo = f'{base}/images/logos/aidea-logo.png'
    base_display = base.replace('https://', '').replace('http://', '')
    return f"""\
<div style="margin:0;padding:24px 12px;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
   <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;
                  box-shadow:0 1px 3px rgba(0,0,0,0.08);">
      <tr>
        <td style="background:#3b5bdb;padding:32px 24px;text-align:center;">
          <span style="display:inline-block;background:#ffffff;border-radius:10px;padding:12px 18px;">
            <img src="{logo}" alt="AIDEA" width="140" style="display:block;height:auto;max-width:140px;">
          </span>
          <div style="color:#dbe4ff;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-top:14px;">
            Password reset
          </div>
        </td>
      </tr>
      <tr>
        <td style="padding:32px 32px 12px;">
          <p style="font-size:20px;font-weight:bold;color:#111827;margin:0 0 6px;">Hello {name},</p>
          <h1 style="font-size:22px;color:#1e3a8a;margin:0 0 16px;">Reset your password</h1>
          <p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 24px;">
            We received a request to reset your AIDEA password. Click the button below to choose a new one.
          </p>
          <p style="text-align:center;margin:0 0 24px;">
            <a href="{link}" style="display:inline-block;padding:13px 30px;background:#3b5bdb;color:#ffffff;
               text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px;">Reset password</a>
          </p>
          <p style="font-size:13px;color:#6b7280;line-height:1.6;margin:0 0 4px;">
            Or paste this link into your browser:
          </p>
          <p style="font-size:13px;margin:0 0 24px;word-break:break-all;">
            <a href="{link}" style="color:#3b5bdb;">{link}</a>
          </p>
          <p style="font-size:13px;color:#6b7280;line-height:1.6;margin:0;">
            If you didn't request this, you can safely ignore this email — your password will stay the same.
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8fafc;padding:24px;text-align:center;border-top:1px solid #eef0f4;">
          <p style="font-size:14px;font-weight:bold;color:#374151;margin:0 0 6px;">
            ICCS Team —
            <a href="https://imu.ntua.gr/wp/" style="color:#374151;">Information Management Unit</a>
          </p>
          <p style="margin:0 0 8px;">
            <a href="{base}" style="color:#3b5bdb;font-size:13px;text-decoration:none;">{base_display}</a>
          </p>
          <p style="font-size:12px;color:#9ca3af;margin:0;">
            This message was sent automatically by the AIDEA platform.
          </p>
        </td>
      </tr>
    </table>
   </td></tr>
  </table>
</div>"""


class PasswordResetRequestView(APIView):
    """POST /api/auth/password-reset/ {email} — email a reset link.

    Always returns the same response so it can't be used to probe which
    email addresses have accounts.
    """
    permission_classes = [AllowAny]
    # Limit reset requests per target email and per source IP.
    throttle_classes = [PasswordResetEmailThrottle, PasswordResetIPThrottle]

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
            'ICCS Team — Information Management Unit\n'
            f'{settings.FRONTEND_BASE_URL}'
        )
        html = _reset_email_html(name, link)
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
