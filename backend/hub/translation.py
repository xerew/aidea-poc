"""Ollama-backed text translation (Phase 2). Network I/O is isolated in
_ollama_generate so tests can mock it — no test hits Ollama."""
import json
import os
import urllib.error
import urllib.request

LANGUAGE_NAMES = {
    'en': 'English', 'el': 'Greek', 'fr': 'French', 'es': 'Spanish',
    'it': 'Italian', 'fi': 'Finnish', 'sv': 'Swedish', 'no': 'Norwegian',
    'de': 'German',
}

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama-tunnel:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma3-translator')
_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '120'))
# Ollama validates the Host header to block DNS-rebinding, accepting only
# localhost/127.0.0.1. When reached over the SSH tunnel the URL host is
# `ollama-tunnel`, which Ollama rejects with 403 — so we send the Host header
# it trusts. The tunnel forwards to 127.0.0.1 on the remote regardless.
OLLAMA_HOST_HEADER = os.getenv('OLLAMA_HOST_HEADER', 'localhost:11434')


class TranslationError(Exception):
    pass


def _ollama_generate(prompt: str) -> str:
    payload = json.dumps({'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False}).encode()
    req = urllib.request.Request(
        f'{OLLAMA_URL}/api/generate', data=payload,
        headers={'Content-Type': 'application/json', 'Host': OLLAMA_HOST_HEADER},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise TranslationError(str(exc)) from exc
    text = (data.get('response') or '').strip()
    if not text:
        raise TranslationError('Empty response from Ollama.')
    return text


def translate_text(text: str, source: str, target: str) -> str:
    if not text or not text.strip():
        return text
    if source == target:
        return text
    src = LANGUAGE_NAMES.get(source, source)
    tgt = LANGUAGE_NAMES.get(target, target)
    prompt = (
        f'Translate the following text from {src} to {tgt}. '
        f'Output only the translation, with no notes, quotes, or explanation.\n\n{text}'
    )
    return _ollama_generate(prompt)
