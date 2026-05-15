from rest_framework.response import Response
from rest_framework.views import APIView

from hub.serializers.profile import ProfilePreferencesSerializer
from hub.views.permissions import IsTeacher


class ProfilePreferencesView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        serializer = ProfilePreferencesSerializer(request.user.profile)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfilePreferencesSerializer(
            request.user.profile, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        from hub.tasks import compute_user_recommendations
        compute_user_recommendations.delay(request.user.id)

        return Response(serializer.data)
