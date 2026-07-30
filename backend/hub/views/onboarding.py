from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import OnboardingDimension, SelfEfficacyAttempt, SelfEfficacyConfig
from hub.models.pathway import LearningPath, UserLearningPath
from hub.self_efficacy import BAND_TO_COMPETENCY, compute_results
from hub.serializers.onboarding import (
    OnboardingDimensionSerializer,
    OnboardingSubmitSerializer,
    SelfEfficacySubmitSerializer,
)
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


def finalize_placement(user, score: int) -> LearningPath:
    """Persist the competency score and (re)assign the learning path, pathway and
    recommendations. Shared by onboarding (default beginner) and self-efficacy
    completion (score derived from the overall band)."""
    profile = user.profile
    profile.competency_score = score
    profile.save(update_fields=['competency_score'])

    path = assign_path(score)
    from hub.pathway_gen import generate_pathway
    UserLearningPath.objects.update_or_create(
        user=user,
        defaults={'path': path, 'course_ids': generate_pathway(user)},
    )

    from hub.tasks import compute_user_recommendations
    compute_user_recommendations.delay(user.id)
    return path


def _active_dimensions():
    return (
        OnboardingDimension.objects
        .filter(is_active=True)
        .prefetch_related('questions')
    )


def _used_current_window(user, config):
    """True if the teacher already recorded an attempt within the currently-open
    retake window — they get exactly one retake per window."""
    if not config.retake_opened_at:
        return False
    latest = user.self_efficacy_attempts.order_by('-created_at').first()
    return bool(latest and latest.created_at >= config.retake_opened_at)


def can_retake(user, config):
    return (
        user.profile.self_efficacy_completed_at is not None
        and config.retake_open
        and not _used_current_window(user, config)
    )


def self_efficacy_payload(request, results=None):
    """Serialize the assessment for the current teacher: the dimensions/questions
    (localized), their saved answers, per-dimension scores and completion +
    retake state."""
    profile = request.user.profile
    dimensions = list(_active_dimensions())
    if results is None:
        results = compute_results(profile.self_efficacy_answers, dimensions)
    scores = {d['slug']: d for d in results['dimensions']}
    dim_data = OnboardingDimensionSerializer(
        dimensions, many=True, context={'lang': profile.language},
    ).data
    for dim in dim_data:
        s = scores.get(dim['slug'], {})
        dim['average'] = s.get('average')
        dim['band'] = s.get('band')

    config = SelfEfficacyConfig.get()
    return {
        'completed': profile.self_efficacy_completed_at is not None,
        # Teachers can redo the assessment only once per admin-opened window.
        'can_retake': can_retake(request.user, config),
        'attempt_count': request.user.self_efficacy_attempts.count(),
        'answers': profile.self_efficacy_answers or {},
        'dimensions': dim_data,
        'overall_average': results['overall_average'],
        'overall_band': results['overall_band'],
        'answered': results['answered'],
        'total': results['total'],
    }


class OnboardingView(APIView):
    """Quick profile step (subject/teaching level/goals) completed at
    registration. The AI self-efficacy assessment is separate and skippable."""
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

        profile = request.user.profile
        profile.subject              = data['subject']
        profile.teaching_level       = data['teaching_level']
        profile.goals                = data['goals']
        profile.onboarding_completed = True
        profile.save()

        # Everyone starts on the beginner path; completing the self-efficacy
        # assessment later refines the competency score and re-places them.
        path = finalize_placement(request.user, profile.competency_score)

        return Response({
            'competency_score': profile.competency_score,
            'competency_level': get_competency_level(profile.competency_score),
            'pathway_id':   path.id,
            'pathway_name': path.name,
        })


class SelfEfficacyView(APIView):
    """GET  → the 6 dimensions with their questions, the learner's saved answers
              and (if all answered) their per-dimension scores and bands.
       POST → merge submitted answers (partial saves allowed). Once every active
              question is answered, finalize: snapshot the attempt, set
              competency_score from the overall band and re-place the learner.
              A completed assessment is read-only until an admin opens a retake."""
    permission_classes = [IsTeacher]

    def get(self, request):
        return Response(self_efficacy_payload(request))

    def post(self, request):
        profile = request.user.profile
        if profile.self_efficacy_completed_at is not None:
            return Response(
                {'detail': 'Assessment already completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SelfEfficacySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incoming = serializer.validated_data['answers']

        merged = {str(k): v for k, v in (profile.self_efficacy_answers or {}).items()}
        merged.update({str(k): v for k, v in incoming.items()})
        profile.self_efficacy_answers = merged

        results = compute_results(merged, list(_active_dimensions()))
        finalized = False
        if results['completed']:
            profile.self_efficacy_completed_at = timezone.now()
            finalized = True
        profile.save(update_fields=['self_efficacy_answers', 'self_efficacy_completed_at'])

        if finalized:
            competency = BAND_TO_COMPETENCY[results['overall_band']]
            SelfEfficacyAttempt.objects.create(
                user=request.user,
                answers=merged,
                dimension_scores={
                    d['slug']: {'average': d['average'], 'band': d['band']}
                    for d in results['dimensions']
                },
                overall_average=results['overall_average'],
                overall_band=results['overall_band'],
                competency_score=competency,
            )
            finalize_placement(request.user, competency)

        return Response(self_efficacy_payload(request, results))


class SelfEfficacyRetakeView(APIView):
    """POST → start a fresh attempt. Allowed only while an admin has opened the
    retake window; the previous attempt stays in the history."""
    permission_classes = [IsTeacher]

    def post(self, request):
        config = SelfEfficacyConfig.get()
        profile = request.user.profile
        if profile.self_efficacy_completed_at is None:
            return Response(
                {'detail': 'No completed assessment to retake.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not config.retake_open:
            return Response(
                {'detail': 'Retaking the assessment is not currently open.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if _used_current_window(request.user, config):
            return Response(
                {'detail': 'You have already retaken the assessment this round.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        profile.self_efficacy_answers = {}
        profile.self_efficacy_completed_at = None
        profile.save(update_fields=['self_efficacy_answers', 'self_efficacy_completed_at'])
        return Response(self_efficacy_payload(request))
