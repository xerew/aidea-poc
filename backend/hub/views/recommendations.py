from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.recommendations import (
    CourseRecommendation,
    RecommendationConfig,
    RecommendationEvent,
)
from hub.serializers.pathway import RecommendationSerializer
from hub.views.permissions import IsTeacher


class RecommendationsView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        recs = (
            CourseRecommendation.objects
            .filter(user=request.user)
            .select_related('course__pillar')
            .order_by('-score')
        )
        return Response(RecommendationSerializer(recs, many=True).data)


class RecommendationEventView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request):
        from hub.serializers.recommendations import RecommendationEventSerializer

        serializer = RecommendationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

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
