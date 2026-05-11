from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.recommendations import CourseRecommendation
from hub.serializers.pathway import RecommendationSerializer
from hub.views.permissions import IsTeacher


class RecommendationsView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        recs = (
            CourseRecommendation.objects
            .filter(user=request.user)
            .select_related('course__pillar')
            .order_by('-score')[:5]
        )
        return Response(RecommendationSerializer(recs, many=True).data)
