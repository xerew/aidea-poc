"""Country -> UI language defaults (Phase 1 i18n). Unmapped -> 'en'."""

COUNTRY_TO_LANGUAGE = {
    'GR': 'el', 'CY': 'el',
    'FR': 'fr', 'MC': 'fr', 'LU': 'fr',
    'ES': 'es', 'MX': 'es', 'AR': 'es', 'CO': 'es', 'CL': 'es', 'PE': 'es',
    'VE': 'es', 'EC': 'es', 'GT': 'es', 'CU': 'es', 'BO': 'es', 'DO': 'es',
    'HN': 'es', 'PY': 'es', 'SV': 'es', 'NI': 'es', 'CR': 'es', 'PA': 'es', 'UY': 'es',
    'IT': 'it', 'SM': 'it',
    'FI': 'fi',
    'SE': 'sv',
    'NO': 'no',
    'DE': 'de', 'AT': 'de', 'CH': 'de', 'LI': 'de',
}


def language_for_country(country_code: str) -> str:
    return COUNTRY_TO_LANGUAGE.get((country_code or '').upper(), 'en')
