from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Subject
from hub.serializers import SubjectSerializer


class SubjectsView(APIView):
    """GET /api/subjects/ — active subjects for onboarding, profile and authoring."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subjects = Subject.objects.filter(is_active=True)
        return Response(SubjectSerializer(subjects, many=True).data)
