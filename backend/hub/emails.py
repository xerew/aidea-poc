"""Transactional emails (welcome, email verification, assignment reviewed).

All sends are best-effort: a mail failure is logged but never breaks the request
that triggered it. Links point at FRONTEND_BASE_URL; branding matches the
password-reset email.
"""
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.utils.html import escape

logger = logging.getLogger(__name__)


def _html_text(value):
    """Escape user-supplied text for safe inclusion in an HTML email, keeping
    line breaks."""
    return escape(value or '').replace('\n', '<br>')

# ── Email-verification token (stateless, signed, 7-day expiry) ────────────────
_VERIFY_SALT = 'aidea.email-verify'
_VERIFY_MAX_AGE = 60 * 60 * 24 * 7


def make_verify_token(user) -> str:
    return signing.dumps({'uid': user.pk}, salt=_VERIFY_SALT)


def read_verify_token(token: str):
    """Return the user id encoded in a verification token, or None if the token
    is invalid or expired."""
    try:
        data = signing.loads(token, salt=_VERIFY_SALT, max_age=_VERIFY_MAX_AGE)
    except (signing.BadSignature, signing.SignatureExpired):
        return None
    return data.get('uid')


# ── Branded HTML shell ────────────────────────────────────────────────────────
def _shell(*, name, tag, heading, paragraphs, cta_label=None, cta_link=None):
    base = settings.FRONTEND_BASE_URL
    logo = f'{base}/images/logos/aidea-logo.png'
    base_display = base.replace('https://', '').replace('http://', '')
    body = ''.join(
        f'<p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 16px;">{p}</p>'
        for p in paragraphs
    )
    cta = ''
    if cta_label and cta_link:
        cta = f"""
          <p style="text-align:center;margin:8px 0 20px;">
            <a href="{cta_link}" style="display:inline-block;padding:13px 30px;background:#3b5bdb;
               color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px;">{cta_label}</a>
          </p>
          <p style="font-size:13px;color:#6b7280;margin:0 0 4px;">Or paste this link into your browser:</p>
          <p style="font-size:13px;margin:0 0 8px;word-break:break-all;">
            <a href="{cta_link}" style="color:#3b5bdb;">{cta_link}</a>
          </p>"""
    return f"""\
<div style="margin:0;padding:24px 12px;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;
                  box-shadow:0 1px 3px rgba(0,0,0,0.08);">
      <tr>
        <td style="background:#3b5bdb;padding:32px 24px;text-align:center;">
          <span style="display:inline-block;background:#ffffff;border-radius:10px;padding:12px 18px;">
            <img src="{logo}" alt="AIDEA" width="140" style="display:block;height:auto;max-width:140px;">
          </span>
          <div style="color:#dbe4ff;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-top:14px;">
            {tag}
          </div>
        </td>
      </tr>
      <tr>
        <td style="padding:32px 32px 12px;">
          <p style="font-size:20px;font-weight:bold;color:#111827;margin:0 0 6px;">Hello {name},</p>
          <h1 style="font-size:22px;color:#1e3a8a;margin:0 0 16px;">{heading}</h1>
          {body}{cta}
        </td>
      </tr>
      <tr>
        <td style="background:#f8fafc;padding:24px;text-align:center;border-top:1px solid #eef0f4;">
          <p style="font-size:14px;font-weight:bold;color:#374151;margin:0 0 6px;">
            ICCS Team — <a href="https://imu.ntua.gr/wp/" style="color:#374151;">Information Management Unit</a>
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
  </td></tr></table>
</div>"""


def _send(*, to, subject, name, tag, heading, paragraphs, cta_label=None, cta_link=None):
    if not to:
        return
    text = f'Hello {name},\n\n' + '\n\n'.join(paragraphs)
    if cta_link:
        text += f'\n\n{cta_label or "Open"}: {cta_link}'
    text += '\n\nICCS Team — Information Management Unit\n' + settings.FRONTEND_BASE_URL
    html = _shell(name=name, tag=tag, heading=heading, paragraphs=paragraphs,
                  cta_label=cta_label, cta_link=cta_link)
    try:
        send_mail(
            subject=subject,
            message=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            html_message=html,
            fail_silently=False,
        )
    except Exception as exc:  # pragma: no cover - mail transport failure
        logger.warning('Failed to send "%s" to %s: %s', subject, to, exc)


# ── Public senders ────────────────────────────────────────────────────────────
def send_welcome_email(user):
    name = user.get_full_name() or user.username
    _send(
        to=user.email,
        subject='Welcome to AIDEA',
        name=name,
        tag='Welcome',
        heading='Welcome to AIDEA',
        paragraphs=[
            'Your AIDEA account is ready. AIDEA helps teachers learn to use, teach '
            'about, and prepare students for AI through short, practical courses.',
            'A good first step is the quick onboarding and the AI Competency '
            'self-assessment — they tailor your learning path.',
        ],
        cta_label='Go to AIDEA',
        cta_link=settings.FRONTEND_BASE_URL,
    )


def send_verification_email(user):
    if not user.email:
        return
    token = make_verify_token(user)
    link = f'{settings.FRONTEND_BASE_URL}/verify-email/{token}'
    name = user.get_full_name() or user.username
    _send(
        to=user.email,
        subject='Confirm your AIDEA email',
        name=name,
        tag='Confirm your email',
        heading='Confirm your email address',
        paragraphs=[
            'Please confirm this is your email address so we can keep your AIDEA '
            'account secure and send you important updates.',
            "If you didn't create an AIDEA account, you can ignore this email.",
        ],
        cta_label='Confirm email',
        cta_link=link,
    )


def send_assignment_reviewed_email(submission):
    user = submission.user
    if not user.email:
        return
    lesson = submission.lesson
    course = lesson.module.course
    approved = submission.status == submission.Status.APPROVED
    outcome = 'approved' if approved else 'sent back with change requests'
    link = f'{settings.FRONTEND_BASE_URL}/courses/{course.id}/learn/{lesson.id}'
    paragraphs = [
        f'Your submission for “{lesson.title}” in “{course.title}” has been '
        f'reviewed and {outcome}.',
    ]
    if submission.feedback:
        paragraphs.append(f'<strong>Reviewer feedback:</strong><br>{_html_text(submission.feedback)}')
    if not approved:
        paragraphs.append('Open the lesson to make the requested changes and resubmit.')
    _send(
        to=user.email,
        subject=f'Your submission was {"approved" if approved else "reviewed"}',
        name=user.get_full_name() or user.username,
        tag='Assignment reviewed',
        heading='Your submission was reviewed',
        paragraphs=paragraphs,
        cta_label='Open the lesson',
        cta_link=link,
    )


def send_access_request_email(access_request):
    """Notify every admin that a user has requested content-creator access."""
    from django.contrib.auth.models import User

    requester = access_request.user
    req_name = requester.get_full_name() or requester.username
    contact = requester.email or requester.username
    link = f'{settings.FRONTEND_BASE_URL}/admin/users'
    admins = (
        User.objects.filter(profile__user_type='admin', is_active=True)
        .exclude(email='')
    )
    for admin in admins:
        _send(
            to=admin.email,
            subject='New content-creator access request',
            name=admin.get_full_name() or admin.username,
            tag='Access request',
            heading='New content-creator access request',
            paragraphs=[
                f'<strong>{_html_text(req_name)}</strong> ({_html_text(contact)}) has '
                'requested content-creator access.',
                f'<strong>Their message:</strong><br>{_html_text(access_request.message)}',
                'Review it in the Admin panel under Access Requests, where you can '
                'approve it as a content creator or an AIDEA partner.',
            ],
            cta_label='Open the Admin panel',
            cta_link=link,
        )

