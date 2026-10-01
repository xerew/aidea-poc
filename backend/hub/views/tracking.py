from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import LearnerActivityConfig
from hub.throttling import TrackingUserThrottle
from hub.tracking import ingest


class TrackingView(APIView):
    """POST /api/tracking/ — the activity page's time and interaction data
    (see hub/tracking.py). 204 means tracking is switched off: the page stops."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [TrackingUserThrottle]

    def post(self, request):
        if not LearnerActivityConfig.get().tracking_enabled:
            return Response(status=status.HTTP_204_NO_CONTENT)
        visits, events = ingest(request.user, request.data)
        return Response({'visits': visits, 'events': events})
