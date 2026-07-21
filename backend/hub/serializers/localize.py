"""Learner-facing language resolution helpers (Phase 2 translations).

Fields NEVER render blank: a missing translation falls back to the
original field value.
"""


def viewer_language(context):
    request = context.get('request')
    profile = getattr(getattr(request, 'user', None), 'profile', None)
    return getattr(profile, 'language', 'en') or 'en'


def localized(obj, field, lang):
    # A translation for the viewer's language wins whenever one exists. Don't
    # special-case 'en': a course may be authored in another source language
    # and translated INTO English, and a course is never translated into its
    # own source language, so when lang == source there is simply no entry and
    # we fall back to the base field.
    if lang:
        value = (obj.translations or {}).get(lang, {}).get(field)
        if value:
            return value
    return getattr(obj, field)
