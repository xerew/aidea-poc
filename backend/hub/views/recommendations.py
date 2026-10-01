from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.recommendations import (
    CourseRecommendation,
    RecommendationConfig,
    RecommendationEvent,
)
from hub.serializers.pathway import RecommendationSerializer
from hub.views.permissions import HasProfile


def records_recommendation_events(user):
    """Shown/click/enrol events tune the recommendation weights and are study
    data, so only teachers' events are stored. Staff (creators, partners,
    admins) see recommendations but don't shape them."""
    profile = getattr(user, 'profile', None)
    return profile is not None and profile.user_type == 'teacher'


class RecommendationsView(APIView):
    permission_classes = [HasProfile]

    def get(self, request):
        from hub.study_logic import active_group
        # Recommendations come from onboarding, for every role; the fixed
        # (control) study group gets no personalised recommendations.
        if not request.user.profile.onboarding_completed or active_group(request.user) == 'fixed':
            return Response([])
        recs = (
            CourseRecommendation.objects
            .filter(user=request.user, course__is_published=True)
            .select_related('course__pillar')
            .order_by('-score')
        )
        return Response(RecommendationSerializer(recs, many=True, context={'request': request}).data)


class RecommendationEventView(APIView):
    permission_classes = [HasProfile]

    def post(self, request):
        from hub.serializers.recommendations import RecommendationEventSerializer

        serializer = RecommendationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        if not records_recommendation_events(request.user):
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        config = RecommendationConfig.get()
        weights_snapshot = {
            'alpha':         config.alpha,
            'beta':          config.beta,
            'gamma':         config.gamma,
            'style_boost':   config.style_boost,
            'bandit_active': config.bandit_active,
        }

        RecommendationEvent.objects.create(
            user=request.user,
            course_id=d['course_id'],
            event_type=d['event_type'],
            rank=d['rank'],
            source=d['source'],
            weights_snapshot=weights_snapshot,
        )
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
