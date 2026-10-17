"""What the AI reviewer gets to see from a submission, and duplicate checks.

Only files inside MEDIA_ROOT are read (uploaded attachments); anything else is
treated as a link. Corrupt or unreadable files are skipped, never fatal."""
import base64
import hashlib
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

MAX_IMAGE_SIDE = 1280
MAX_IMAGES = 6
MAX_TEXT_CHARS = 20000
DHASH_MAX_DISTANCE = 6
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


@dataclass
class Evidence:
    text: str = ''
    documents: list = field(default_factory=list)
    images: list = field(default_factory=list)
    links: list = field(default_factory=list)
    fingerprints: list = field(default_factory=list)


def media_path(url):
    path = unquote(urlparse(str(url)).path)
    if not path.startswith(settings.MEDIA_URL):
        return None
    root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (root / path[len(settings.MEDIA_URL):]).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def extract_text(path):
    suffix = Path(path).suffix.lower()
    try:
        if suffix == '.pdf':
            from pypdf import PdfReader
            text = '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)
        elif suffix == '.docx':
            import docx
            text = '\n'.join(p.text for p in docx.Document(str(path)).paragraphs)
        elif suffix == '.txt':
            text = Path(path).read_text(encoding='utf-8', errors='replace')
        else:
            return ''
    except Exception as exc:  # noqa: BLE001 — any parser failure means "no text"
        log.info('AI review: could not read %s: %s', path, exc)
        return ''
    return text.strip()[:MAX_TEXT_CHARS]


def image_b64(path):
    try:
        with Image.open(path) as img:
            img = img.convert('RGB')
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return base64.b64encode(buffer.getvalue()).decode()


def _dhash(path):
    try:
        with Image.open(path) as img:
            small = img.convert('L').resize((9, 8))
    except (UnidentifiedImageError, OSError, ValueError):
        return ''
    pixels = list(small.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return f'{bits:016x}'


def fingerprint(path):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    dhash = _dhash(path) if Path(path).suffix.lower() in IMAGE_SUFFIXES else ''
    return {'sha256': digest, 'dhash': dhash}


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')


def gather(submission):
    ev = Evidence(text=(submission.text or '').strip()[:MAX_TEXT_CHARS])
    for att in submission.attachments or []:
        name = att.get('name') or att.get('url', '')
        path = media_path(att.get('url', ''))
        if att.get('type') == 'video' or path is None:
            ev.links.append(f"{name} ({att.get('url', '')})" if name != att.get('url') else name)
            continue
        ev.fingerprints.append({'name': name, **fingerprint(path)})
        if path.suffix.lower() in IMAGE_SUFFIXES:
            encoded = image_b64(path) if len(ev.images) < MAX_IMAGES else None
            if encoded:
                ev.images.append({'name': name, 'b64': encoded})
        else:
            text = extract_text(path)
            if text:
                ev.documents.append({'name': name, 'text': text})
    return ev


def find_duplicates(submission, fingerprints):
    """Files matching another learner's submission to the same assignment."""
    from hub.models import AIReview
    others = (
        AIReview.objects.filter(submission__resource_id=submission.resource_id)
        .exclude(submission__user_id=submission.user_id)
        .select_related('submission__user')
    )
    found, seen = [], set()
    for other in others:
        for theirs in (other.checks or {}).get('fingerprints', []):
            for mine in fingerprints:
                if mine['sha256'] == theirs.get('sha256'):
                    match = 'identical'
                elif mine.get('dhash') and theirs.get('dhash') and hamming(mine['dhash'], theirs['dhash']) <= DHASH_MAX_DISTANCE:
                    match = 'similar'
                else:
                    continue
                key = (other.submission_id, mine['name'])
                if key in seen:
                    continue
                seen.add(key)
                user = other.submission.user
                found.append({
                    'submission_id': other.submission_id, 'learner': user.get_full_name() or user.username,
                    'file': mine['name'], 'match': match,
                })
    return found
