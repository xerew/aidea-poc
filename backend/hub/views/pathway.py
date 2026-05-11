from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models.pathway import UserLearningPath
from hub.serializers.pathway import UserLearningPathSerializer
from hub.views.permissions import IsTeacher


class PathwayView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            user_path = (
                UserLearningPath.objects
                .select_related('path', 'user__profile')
                .get(user=request.user)
            )
        except UserLearningPath.DoesNotExist:
            return Response(
                {'detail': 'No pathway assigned. Complete onboarding first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserLearningPathSerializer(
            user_path, context={'user': request.user, 'request': request},
        )
        return Response(serializer.data)
