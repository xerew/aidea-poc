from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.pathway import LearningPath, UserLearningPath
from hub.serializers.onboarding import OnboardingSubmitSerializer
from hub.views.permissions import IsTeacher

ANSWER_SCORES = {
    'q3': {'b': 2, 'c': 1},
    'q4': {'b': 2, 'c': 1},
    'q5': {'b': 2, 'c': 1, 'd': 1},
}


def score_answers(answers: dict) -> int:
    return sum(ANSWER_SCORES.get(q, {}).get(a, 0) for q, a in answers.items())


def get_competency_level(score: int) -> str:
    if score <= 2:
        return 'beginner'
    if score <= 4:
        return 'intermediate'
    return 'advanced'


def assign_path(score: int) -> LearningPath:
    path = LearningPath.objects.filter(
        competency_min__lte=score,
        competency_max__gte=score,
    ).first()
    if not path:
        path = LearningPath.objects.get(slug='beginner-foundations')
    return path


class OnboardingView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        profile = request.user.profile
        return Response({
            'completed': profile.onboarding_completed,
            'competency_level': (
                get_competency_level(profile.competency_score)
                if profile.onboarding_completed else None
            ),
        })

    def post(self, request):
        serializer = OnboardingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        score = score_answers(data['answers'])
        level = get_competency_level(score)
        path  = assign_path(score)

        profile = request.user.profile
        profile.subject_area         = data['subject_area']
        profile.teaching_level       = data['teaching_level']
        profile.goals                = data['goals']
        profile.competency_score     = score
        profile.onboarding_completed = True
        profile.save()

        UserLearningPath.objects.update_or_create(
            user=request.user,
            defaults={'path': path},
        )

        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(request.user.id)

        return Response({
            'competency_score': score,
            'competency_level': level,
            'pathway_id':   path.id,
            'pathway_name': path.name,
        })
