"""Talking to the self-hosted review model (Ollama /api/chat, JSON-schema
output, images). `_chat` is the only network call, so tests mock it."""
import json
import os
import re
import urllib.error
import urllib.request

from django.utils.html import strip_tags

from hub.translation import LANGUAGE_NAMES, OLLAMA_HOST_HEADER, OLLAMA_URL

PROMPT_VERSION = '2026-10-16.1'
TIMEOUT = int(os.getenv('AI_REVIEW_TIMEOUT', '300'))
STATUSES = ('met', 'partly_met', 'not_met', 'cannot_judge')
VERDICTS = ('approve', 'changes_requested', 'unsure')

REVIEW_SCHEMA = {
    'type': 'object',
    'properties': {
        'criteria': {'type': 'array', 'items': {
            'type': 'object',
            'properties': {'id': {'type': 'string'}, 'status': {'type': 'string', 'enum': list(STATUSES)},
                           'reason': {'type': 'string'}},
            'required': ['id', 'status', 'reason'],
        }},
        'verdict': {'type': 'string', 'enum': list(VERDICTS)},
        'confidence': {'type': 'number'},
        'learner_feedback': {'type': 'string'},
        'reviewer_notes': {'type': 'string'},
    },
    'required': ['criteria', 'verdict', 'confidence', 'learner_feedback', 'reviewer_notes'],
}
RUBRIC_SCHEMA = {
    'type': 'object',
    'properties': {'criteria': {'type': 'array', 'items': {
        'type': 'object',
        'properties': {'name': {'type': 'string'}, 'met': {'type': 'string'}, 'required': {'type': 'boolean'}},
        'required': ['name', 'met', 'required'],
    }}},
    'required': ['criteria'],
}

SYSTEM = (
    'You review teachers\' assignment submissions for an AI-literacy course. '
    'Judge each rubric criterion only from the evidence given; if the evidence cannot show it '
    '(e.g. a video you cannot watch), use "cannot_judge". Be fair and specific. '
    'Suggest "approve" only when every required criterion is met; "changes_requested" when a '
    'required criterion is clearly not met; otherwise "unsure". Confidence is how sure you are of '
    'the verdict (0 to 1). Answer only with JSON matching the schema.'
)


class ReviewModelError(Exception):
    pass


class ModelOffline(ReviewModelError):
    pass


def _chat(messages, schema, model):
    payload = json.dumps({
        'model': model, 'messages': messages, 'stream': False, 'format': schema,
        'options': {'temperature': 0},
    }).encode()
    request = urllib.request.Request(
        f'{OLLAMA_URL}/api/chat', data=payload,
        headers={'Content-Type': 'application/json', 'Host': OLLAMA_HOST_HEADER},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelOffline(str(exc)) from exc
    except ValueError as exc:
        raise ReviewModelError(f'Unreadable response: {exc}') from exc
    return (data.get('message') or {}).get('content') or ''


def _plain(html):
    return re.sub(r'\s+', ' ', strip_tags(html or '')).strip()


def build_messages(*, instructions, criteria, examples, evidence, checks, language):
    rubric = '\n'.join(
        f"[{c['id']}] {c['name']} — met when: {c['met']} ({'required' if c.get('required') else 'nice to have'})"
        for c in criteria
    )
    parts = [
        f'ASSIGNMENT INSTRUCTIONS:\n{_plain(instructions)}',
        f'RUBRIC (answer for every id):\n{rubric}',
    ]
    for i, ex in enumerate(examples, start=1):
        parts.append(f"EXAMPLE {i} (correct verdict: {ex['verdict']}; why: {ex.get('reason', '')}):\n{ex.get('text', '')}")
    parts.append(f'SUBMISSION TEXT:\n{evidence.text or "(none)"}')
    for doc in evidence.documents:
        parts.append(f"ATTACHED DOCUMENT {doc['name']}:\n{doc['text']}")
    if evidence.images:
        parts.append('ATTACHED IMAGES (in order): ' + ', '.join(i['name'] for i in evidence.images))
    if evidence.links:
        parts.append('LINKS (cannot be watched or opened by you): ' + '; '.join(evidence.links))
    duplicates = (checks or {}).get('duplicates') or []
    if duplicates:
        parts.append('CHECK — same file also submitted by another learner: ' + '; '.join(
            f"{d['file']} ({d['match']}, also from {d['learner']})" for d in duplicates))
    parts.append(f"Write learner_feedback and each criterion reason in {LANGUAGE_NAMES.get(language, 'English')}. "
                 'Write reviewer_notes in English.')
    user = {'role': 'user', 'content': '\n\n'.join(parts)}
    if evidence.images:
        user['images'] = [i['b64'] for i in evidence.images]
    return [{'role': 'system', 'content': SYSTEM}, user]


def _load_json(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        match = re.search(r'\{.*\}', raw or '', re.S)
        if not match:
            raise ReviewModelError('No JSON in the answer.') from None
        try:
            return json.loads(match.group(0))
        except ValueError as exc:
            raise ReviewModelError(f'Malformed JSON: {exc}') from exc


def parse_review(raw, criteria):
    data = _load_json(raw)
    if not isinstance(data, dict):
        raise ReviewModelError('Answer is not an object.')
    results = data.get('criteria')
    wanted = [c['id'] for c in criteria]
    if not isinstance(results, list) or sorted(r.get('id') for r in results if isinstance(r, dict)) != sorted(wanted):
        raise ReviewModelError('Criteria do not match the rubric.')
    by_id = {r['id']: r for r in results}
    out_criteria = []
    for cid in wanted:
        r = by_id[cid]
        if r.get('status') not in STATUSES:
            raise ReviewModelError(f'Bad status for {cid}.')
        out_criteria.append({'id': cid, 'status': r['status'], 'reason': str(r.get('reason', ''))[:1000]})
    if data.get('verdict') not in VERDICTS:
        raise ReviewModelError('Bad verdict.')
    confidence = data.get('confidence')
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ReviewModelError('Bad confidence.')
    return {
        'criteria': out_criteria,
        'verdict': data['verdict'],
        'confidence': round(min(max(float(confidence), 0.0), 1.0), 3),
        'learner_feedback': str(data.get('learner_feedback', ''))[:4000],
        'reviewer_notes': str(data.get('reviewer_notes', ''))[:4000],
    }


def review_submission(*, instructions, criteria, examples, evidence, checks, language, model):
    messages = build_messages(instructions=instructions, criteria=criteria, examples=examples,
                              evidence=evidence, checks=checks, language=language)
    last = None
    for _ in range(2):
        raw = _chat(messages, REVIEW_SCHEMA, model)   # ModelOffline propagates (the task retries later)
        try:
            return parse_review(raw, criteria)
        except ReviewModelError as exc:
            last = exc
    raise last


def draft_rubric(*, title, instructions, language, model):
    prompt = (
        f'Propose 3 to 6 assessment criteria for this assignment. Each has a short name, a one-sentence '
        f'description of what "met" looks like, and whether it is required. Write them in '
        f"{LANGUAGE_NAMES.get(language, 'English')}.\n\nTITLE: {title}\n\nINSTRUCTIONS:\n{_plain(instructions)}"
    )
    data = _load_json(_chat([{'role': 'user', 'content': prompt}], RUBRIC_SCHEMA, model))
    items = data.get('criteria') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ReviewModelError('No criteria proposed.')
    return [
        {'id': f'c{i}', 'name': str(c.get('name', ''))[:120], 'met': str(c.get('met', ''))[:500],
         'required': bool(c.get('required', True))}
        for i, c in enumerate(items[:6], start=1) if isinstance(c, dict) and c.get('name')
    ]
