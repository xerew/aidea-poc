"""Is the translation server (Ollama on the NTUA VM, reached through the
ollama-tunnel SSH container) up?

The latest result lives in the cache so every web/worker process sees it:
checked every 15 minutes by Celery beat, and live whenever someone presses
Translate. Admins are emailed when the server goes offline or comes back.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format

from hub.translation import OLLAMA_HOST_HEADER, OLLAMA_MODEL, OLLAMA_URL

logger = logging.getLogger(__name__)

STATUS_KEY = 'translation_service_status'
PROBE_TIMEOUT = 5  # seconds — the tunnel answers instantly when the VM is up
# Written by the ollama-tunnel container (shared volume): the NTUA address in use.
TUNNEL_STATUS_FILE = os.getenv('OLLAMA_TUNNEL_STATUS_FILE', '/ollama-status/ollama-tunnel.json')


def _reason(exc):
    reason = getattr(exc, 'reason', None) or exc
    return str(reason) or exc.__class__.__name__


def probe():
    """One live check. Returns (online, error_message)."""
    req = urllib.request.Request(f'{OLLAMA_URL}/api/tags', headers={'Host': OLLAMA_HOST_HEADER})
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return False, f'Cannot reach the translation server: {_reason(exc)}'
    names = [m.get('name', '') for m in data.get('models', []) if isinstance(m, dict)]
    if not any(n == OLLAMA_MODEL or n.startswith(f'{OLLAMA_MODEL}:') for n in names):
        return False, f'The translation server is up but the model "{OLLAMA_MODEL}" is not installed.'
    return True, ''


def tunnel_address():
    """(address, since) the ollama-tunnel container is using; (None, None) if unknown."""
    try:
        with open(TUNNEL_STATUS_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return (data.get('host') or None), parse_datetime(data.get('since') or '')
    except (OSError, ValueError, AttributeError, TypeError):
        return None, None


def server_summary():
    """One live line for Django admin: which address is connected, or why not."""
    online, error = probe()
    host, since = tunnel_address()
    when = f' since {date_format(timezone.localtime(since), "j M Y, H:i")}' if since else ''
    if online:
        if host:
            return f'Connected via {host}{when}.'
        return 'Connected (the ollama-tunnel container has not reported its address).'
    trying = f' Trying {host} now.' if host else ''
    return f'Not connected.{trying} {error}'


def get_status():
    """Last recorded status, or None if no check has run yet."""
    return cache.get(STATUS_KEY)


def check_now():
    """Probe, record the result, and email admins if the state changed."""
    online, error = probe()
    now = timezone.now().isoformat()
    previous = get_status()
    changed = previous is None or previous['online'] != online
    status = {
        'online': online,
        'error': error,
        'host': tunnel_address()[0],
        'checked_at': now,
        # When the current state began (kept across checks while it holds).
        'since': now if changed else previous['since'],
    }
    cache.set(STATUS_KEY, status, timeout=None)
    # Alert on a real transition, or on a first check that finds it down.
    if changed and (previous is not None or not online):
        logger.warning('Translation server is now %s. %s', 'online' if online else 'OFFLINE', error)
        from hub.emails import send_translation_service_email
        send_translation_service_email(status)
    return status
