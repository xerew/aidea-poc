"""Best-effort recording for the admin per-user activity page: a failure is
logged and never breaks the request that triggered it."""
import logging

logger = logging.getLogger(__name__)

# Checked in order; the first match wins.
_BROWSERS = (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Opera', 'Opera'), ('Firefox/', 'Firefox'),
             ('Chrome/', 'Chrome'), ('Safari/', 'Safari'))


def parse_user_agent(ua):
    """(device, browser) from a User-Agent header, by plain substring checks."""
    ua = ua or ''
    if not ua:
        return '', 'Other'
    if 'iPad' in ua or 'Tablet' in ua:
        device = 'tablet'
    elif 'Mobi' in ua or 'Android' in ua or 'iPhone' in ua:
        device = 'mobile'
    else:
        device = 'desktop'
    browser = next((name for needle, name in _BROWSERS if needle in ua), 'Other')
    return device, browser


def record_login(request, user):
    """A successful sign-in (or the sign-in that comes with registering)."""
    try:
        from hub.models import LoginRecord
        device, browser = parse_user_agent(request.META.get('HTTP_USER_AGENT'))
        LoginRecord.objects.create(user=user, device=device, browser=browser)
    except Exception as exc:
        logger.warning('Could not record a login for user %s: %s', getattr(user, 'pk', None), exc)
