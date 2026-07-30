from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import (
    OnboardingDimension,
    SelfEfficacyAttempt,
    SelfEfficacyConfig,
    UserProfile,
)
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
    """Whether the teacher may START a fresh retake (not already retaking, one
    per admin-opened window)."""
    profile = user.profile
    return (
        profile.self_efficacy_completed_at is not None
        and not profile.self_efficacy_retaking
        and config.retake_open
        and not _used_current_window(user, config)
    )


def self_efficacy_payload(request):
    """Serialize the assessment for the current teacher: the dimensions/questions
    (localized), the working answers, per-dimension scores and completion +
    retake state.

    While a retake is in progress the questionnaire shows the draft answers, but
    the results bars keep showing the last COMPLETED attempt — so a teacher who
    pauses mid-retake still sees their old review until they finish."""
    profile = request.user.profile
    dimensions = list(_active_dimensions())
    completed = profile.self_efficacy_completed_at is not None
    retaking = profile.self_efficacy_retaking

    # The questionnaire edits the draft while retaking, else the live answers.
    working = profile.self_efficacy_draft if retaking else (profile.self_efficacy_answers or {})
    working_results = compute_results(working, dimensions)

    # The results view reflects the last completed attempt (or the in-progress
    # answers for a first-timer who has nothing completed yet).
    display_source = profile.self_efficacy_answers if completed else working
    display_results = compute_results(display_source, dimensions)

    scores = {d['slug']: d for d in display_results['dimensions']}
    dim_data = OnboardingDimensionSerializer(
        dimensions, many=True, context={'lang': profile.language},
    ).data
    for dim in dim_data:
        s = scores.get(dim['slug'], {})
        dim['average'] = s.get('average')
        dim['band'] = s.get('band')

    config = SelfEfficacyConfig.get()
    return {
        'completed': completed,
        'retaking': retaking,
        'can_retake': can_retake(request.user, config),
        'attempt_count': request.user.self_efficacy_attempts.count(),
        'answers': working,
        'answered': working_results['answered'],
        'total': working_results['total'],
        'dimensions': dim_data,
        'overall_average': display_results['overall_average'],
        'overall_band': display_results['overall_band'],
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
              A completed assessment is read-only until an admin opens a retake.
       Open to every signed-in user (teachers, content creators, partners,
       admins) — only teachers additionally get a learning-path placement."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(self_efficacy_payload(request))

    def post(self, request):
        profile = request.user.profile
        retaking = profile.self_efficacy_retaking
        # A completed assessment is read-only unless the teacher is mid-retake.
        if profile.self_efficacy_completed_at is not None and not retaking:
            return Response(
                {'detail': 'Assessment already completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SelfEfficacySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incoming = serializer.validated_data['answers']

        # A retake edits the draft; a first-timer edits the live answers.
        current = profile.self_efficacy_draft if retaking else profile.self_efficacy_answers
        merged = {str(k): v for k, v in (current or {}).items()}
        merged.update({str(k): v for k, v in incoming.items()})

        results = compute_results(merged, list(_active_dimensions()))
        finalized = results['completed']

        if retaking:
            profile.self_efficacy_draft = merged
            if finalized:
                # Promote the draft to the live, completed answers.
                profile.self_efficacy_answers = merged
                profile.self_efficacy_completed_at = timezone.now()
                profile.self_efficacy_retaking = False
                profile.self_efficacy_draft = {}
        else:
            profile.self_efficacy_answers = merged
            if finalized:
                profile.self_efficacy_completed_at = timezone.now()
        profile.save(update_fields=[
            'self_efficacy_answers', 'self_efficacy_completed_at',
            'self_efficacy_draft', 'self_efficacy_retaking',
        ])

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
            if profile.user_type == UserProfile.UserType.TEACHER:
                # Teachers get re-placed on a learning path; other roles just
                # record their competency.
                finalize_placement(request.user, competency)
            else:
                profile.competency_score = competency
                profile.save(update_fields=['competency_score'])

        return Response(self_efficacy_payload(request))


class SelfEfficacyRetakeView(APIView):
    """POST → start a fresh attempt. Allowed only while an admin has opened the
    retake window; the previous attempt stays in the history."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        config = SelfEfficacyConfig.get()
        profile = request.user.profile
        if profile.self_efficacy_completed_at is None:
            return Response(
                {'detail': 'No completed assessment to retake.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Already mid-retake — just resume the existing draft.
        if profile.self_efficacy_retaking:
            return Response(self_efficacy_payload(request))
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
        # Start a fresh draft; the completed answers/results stay untouched until
        # the retake is finished.
        profile.self_efficacy_retaking = True
        profile.self_efficacy_draft = {}
        profile.save(update_fields=['self_efficacy_retaking', 'self_efficacy_draft'])
        return Response(self_efficacy_payload(request))
