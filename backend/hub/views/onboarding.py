from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import OnboardingQuestion
from hub.models.pathway import LearningPath, UserLearningPath
from hub.serializers.onboarding import OnboardingQuestionSerializer, OnboardingSubmitSerializer
from hub.views.permissions import IsTeacher


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
        questions = OnboardingQuestion.objects.filter(is_active=True).prefetch_related('options')
        return Response({
            'completed': profile.onboarding_completed,
            'competency_level': (
                get_competency_level(profile.competency_score)
                if profile.onboarding_completed else None
            ),
            'questions': OnboardingQuestionSerializer(questions, many=True).data,
        })

    def post(self, request):
        serializer = OnboardingSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # answers is {question_id: OnboardingOption}; competency = sum of points.
        score = sum(option.score for option in data['answers'].values())
        level = get_competency_level(score)
        path  = assign_path(score)

        profile = request.user.profile
        profile.subject              = data['subject']
        profile.teaching_level       = data['teaching_level']
        profile.goals                = data['goals']
        profile.competency_score     = score
        profile.onboarding_completed = True
        profile.save()

        from hub.pathway_gen import generate_pathway
        UserLearningPath.objects.update_or_create(
            user=request.user,
            defaults={'path': path, 'course_ids': generate_pathway(request.user)},
        )

        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(request.user.id)

        return Response({
            'competency_score': score,
            'competency_level': level,
            'pathway_id':   path.id,
            'pathway_name': path.name,
        })
