from collections import Counter

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import PreferenceOption, PreferenceQuestion, UserProfile
from hub.serializers.preference_quiz import PreferenceQuestionSerializer
from hub.tasks import compute_user_recommendations


class PreferenceQuizView(APIView):
    """GET /api/preference-quiz/ — active questions. POST — tally answers, save style."""

    def get(self, request):
        questions = (
            PreferenceQuestion.objects
            .filter(is_active=True)
            .prefetch_related('options')
        )
        return Response(PreferenceQuestionSerializer(questions, many=True).data)

    def post(self, request):
        answers = request.data.get('answers')
        if not isinstance(answers, list) or not answers:
            return Response({'error': 'answers must be a non-empty list.'},
                            status=status.HTTP_400_BAD_REQUEST)

        option_ids = []
        for answer in answers:
            if not isinstance(answer, dict) or not isinstance(answer.get('option_id'), int):
                return Response({'error': 'each answer needs an integer option_id.'},
                                status=status.HTTP_400_BAD_REQUEST)
            option_ids.append(answer['option_id'])

        options = list(
            PreferenceOption.objects
            .filter(id__in=option_ids, question__is_active=True)
            .select_related('question')
        )
        if len(options) != len(set(option_ids)) or len(option_ids) != len(set(option_ids)):
            return Response({'error': 'invalid or duplicate option ids.'},
                            status=status.HTTP_400_BAD_REQUEST)

        seen_questions = set()
        for option in options:
            if option.question_id in seen_questions:
                return Response({'error': 'only one answer per question is allowed.'},
                                status=status.HTTP_400_BAD_REQUEST)
            seen_questions.add(option.question_id)

        counts = Counter(option.maps_to for option in options)
        best = max(counts.values())
        winner = next(
            style for style in UserProfile.LearningStyle.values
            if counts.get(style, 0) == best
        )

        profile = request.user.profile
        profile.learning_style = winner
        profile.save(update_fields=['learning_style'])
        compute_user_recommendations.delay(request.user.id)

        return Response({
            'learning_style': winner,
            'label': UserProfile.LearningStyle(winner).label,
        })
