"""Brute-force / abuse throttles for the unauthenticated auth endpoints.

Login is throttled on two keys at once:
  * per submitted username — protects a targeted account regardless of source
    IP, and (importantly for schools behind one NAT IP) doesn't penalise
    legitimate logins to *different* accounts from the same address;
  * per client IP — a generous backstop so one address can't hammer many
    usernames.

Password reset is throttled per target email (stops inbox-bombing / repeated
reset abuse) plus a per-IP backstop.

Rates live in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']; a None rate
(the default in tests) disables the throttle.
"""
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class _LiveRateThrottle(SimpleRateThrottle):
    """Read the rate from settings on every instantiation. DRF freezes
    THROTTLE_RATES as a class attribute at import time, which ignores
    override_settings (used in tests); reading it live avoids that."""

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)


class LoginIPThrottle(_LiveRateThrottle):
    scope = 'login_ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class LoginUserThrottle(_LiveRateThrottle):
    scope = 'login_user'

    def get_cache_key(self, request, view):
        username = str(request.data.get('username') or '').strip().lower()
        if not username:
            return None  # no username → let the IP throttle handle it
        return self.cache_format % {'scope': self.scope, 'ident': username}


class PasswordResetIPThrottle(_LiveRateThrottle):
    scope = 'pw_reset_ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class PasswordResetEmailThrottle(_LiveRateThrottle):
    scope = 'pw_reset_email'

    def get_cache_key(self, request, view):
        email = str(request.data.get('email') or '').strip().lower()
        if not email:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': email}
