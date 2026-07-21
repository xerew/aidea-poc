"""Learner-facing language resolution helpers (Phase 2 translations).

Fields NEVER render blank: a missing translation falls back to the
original field value.
"""


def viewer_language(context):
    request = context.get('request')
    profile = getattr(getattr(request, 'user', None), 'profile', None)
    return getattr(profile, 'language', 'en') or 'en'


def localized(obj, field, lang):
    if lang and lang != 'en':
        value = (obj.translations or {}).get(lang, {}).get(field)
        if value:
            return value
    return getattr(obj, field)
