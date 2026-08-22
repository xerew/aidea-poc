from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import MaintenanceNotice
from hub.views.permissions import IsAdmin


def _full(notice):
    return {
        'enabled': notice.enabled,
        'message': notice.message,
        'starts_at': notice.starts_at.isoformat() if notice.starts_at else None,
        'ends_at': notice.ends_at.isoformat() if notice.ends_at else None,
    }


class MaintenanceView(APIView):
    """GET → the currently active maintenance notice (or {active: false}).
    Public so it can also inform users on the login screen."""
    permission_classes = [AllowAny]

    def get(self, request):
        notice = MaintenanceNotice.get()
        if not notice.is_active(timezone.now()):
            return Response({'active': False})
        return Response({
            'active': True,
            'message': notice.message,
            'starts_at': notice.starts_at.isoformat() if notice.starts_at else None,
            'ends_at': notice.ends_at.isoformat() if notice.ends_at else None,
        })


class AdminMaintenanceView(APIView):
    """GET/PATCH the maintenance banner (enabled, message, window)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(_full(MaintenanceNotice.get()))

    def patch(self, request):
        notice = MaintenanceNotice.get()
        data = request.data
        if 'enabled' in data:
            notice.enabled = bool(data['enabled'])
        if 'message' in data:
            notice.message = str(data.get('message') or '').strip()
        if 'starts_at' in data:
            notice.starts_at = parse_datetime(data['starts_at']) if data.get('starts_at') else None
        if 'ends_at' in data:
            notice.ends_at = parse_datetime(data['ends_at']) if data.get('ends_at') else None
        notice.save()
        return Response(_full(notice))
