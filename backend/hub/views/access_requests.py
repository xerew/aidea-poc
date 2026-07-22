from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AccessRequest
from hub.serializers.admin import AccessRequestSerializer


class AccessRequestMineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        req = request.user.access_requests.first()  # ordered by -created_at per model Meta
        if req is None:
            return Response(None)
        return Response(AccessRequestSerializer(req).data)


class AccessRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.access_requests.filter(status=AccessRequest.Status.PENDING).exists():
            return Response({'error': 'You already have a pending request.'}, status=400)
        if request.user.profile.user_type in ('content_creator', 'admin'):
            return Response({'error': 'You already have content creator access.'}, status=400)
        message = request.data.get('message', '').strip()
        if not message:
            return Response({'error': 'message is required.'}, status=400)
        req = AccessRequest.objects.create(user=request.user, message=message)
        return Response(AccessRequestSerializer(req).data, status=201)


class AccessRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            req = request.user.access_requests.get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        if req.status != AccessRequest.Status.PENDING:
            return Response({'error': 'Only pending requests can be cancelled.'}, status=400)
        req.delete()
        return Response(status=204)


class AccessRequestSeenView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            req = request.user.access_requests.get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        req.denial_seen = True
        req.save()
        return Response(AccessRequestSerializer(req).data)
