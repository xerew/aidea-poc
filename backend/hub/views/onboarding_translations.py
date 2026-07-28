from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import OnboardingConfig, OnboardingQuestion
from hub.tasks import ONBOARDING_SOURCE_LANGUAGE
from hub.translation import LANGUAGE_NAMES
from hub.views.permissions import IsAdmin


class AdminOnboardingTranslationsView(APIView):
    """Admin control for onboarding-question translations.

    GET   → per-language translation status ('pending'|'done'|'reviewed'|'failed').
    POST  {language} → start an Ollama translation of all active questions.
    PATCH {language, reviewed} → mark a completed translation human-reviewed,
                                 or clear the reviewed mark back to 'done'.
    """
    permission_classes = [IsAdmin]

    def _payload(self, cfg):
        return {
            'source_language': ONBOARDING_SOURCE_LANGUAGE,
            'translation_status': cfg.translation_status or {},
            'has_questions': OnboardingQuestion.objects.filter(is_active=True).exists(),
            'languages': [
                {'code': code, 'label': label}
                for code, label in LANGUAGE_NAMES.items()
                if code != ONBOARDING_SOURCE_LANGUAGE
            ],
        }

    def get(self, request):
        return Response(self._payload(OnboardingConfig.get()))

    def post(self, request):
        language = request.data.get('language')
        if language not in LANGUAGE_NAMES or language == ONBOARDING_SOURCE_LANGUAGE:
            return Response({'detail': 'Invalid or source language.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not OnboardingQuestion.objects.filter(is_active=True).exists():
            return Response({'detail': 'No active onboarding questions to translate.'},
                            status=status.HTTP_400_BAD_REQUEST)
        cfg = OnboardingConfig.get()
        cfg.translation_status[language] = 'pending'
        cfg.save(update_fields=['translation_status'])
        from hub.tasks import translate_onboarding
        translate_onboarding.delay(language)
        return Response(self._payload(cfg), status=status.HTTP_202_ACCEPTED)

    def patch(self, request):
        language = request.data.get('language')
        cfg = OnboardingConfig.get()
        current = (cfg.translation_status or {}).get(language)
        if current is None:
            return Response({'detail': 'That language has no translation.'},
                            status=status.HTTP_400_BAD_REQUEST)

        reviewed = request.data.get('reviewed', True)
        if reviewed:
            if current not in ('done', 'reviewed'):
                return Response({'detail': 'Only a completed translation can be marked reviewed.'},
                                status=status.HTTP_400_BAD_REQUEST)
            cfg.translation_status[language] = 'reviewed'
        elif current == 'reviewed':
            cfg.translation_status[language] = 'done'

        cfg.save(update_fields=['translation_status'])
        return Response(self._payload(cfg))
