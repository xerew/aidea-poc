from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AccessRequest, UserProfile
from hub.serializers.admin import (
    AccessRequestAdminSerializer,
    AdminUserRoleSerializer,
    AdminUserSerializer,
)
from hub.views.permissions import IsAdmin

ROLE_ORDER = {
    UserProfile.UserType.ADMIN:           0,
    UserProfile.UserType.CONTENT_CREATOR: 1,
    UserProfile.UserType.AIDEA_PARTNER:   2,
    UserProfile.UserType.TEACHER:         3,
}


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = (
            User.objects
            .select_related('profile')
            .filter(profile__isnull=False)
        )
        serializer = AdminUserSerializer(users, many=True)
        data = sorted(
            serializer.data,
            key=lambda u: (ROLE_ORDER.get(u['user_type'], 9), u['first_name'], u['last_name']),
        )
        return Response(data)


class AdminUserRoleView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        if pk == request.user.id:
            return Response({'error': 'You cannot change your own role.'}, status=400)
        try:
            user = User.objects.select_related('profile').get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)
        serializer = AdminUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.profile.user_type = serializer.validated_data['user_type']
        user.profile.save()
        return Response(AdminUserSerializer(user).data)


class AdminAccessRequestListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AccessRequest.objects.select_related('user__profile').all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(AccessRequestAdminSerializer(qs, many=True).data)


class AdminAccessRequestReviewView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            req = AccessRequest.objects.select_related('user__profile').get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)

        if req.status != AccessRequest.Status.PENDING:
            return Response({'error': 'This request has already been reviewed.'}, status=400)

        action = request.data.get('action')

        if action == 'approve':
            with transaction.atomic():
                req.status      = AccessRequest.Status.APPROVED
                req.reviewed_by = request.user
                req.reviewed_at = timezone.now()
                req.save()
                req.user.profile.user_type = UserProfile.UserType.CONTENT_CREATOR
                req.user.profile.save()

        elif action == 'deny':
            denial_reason = request.data.get('denial_reason', '').strip()
            if not denial_reason:
                return Response({'error': 'denial_reason is required when denying.'}, status=400)
            req.status        = AccessRequest.Status.DENIED
            req.denial_reason = denial_reason
            req.denial_seen   = False
            req.reviewed_by   = request.user
            req.reviewed_at   = timezone.now()
            req.save()

        else:
            return Response({'error': 'action must be "approve" or "deny".'}, status=400)

        return Response(AccessRequestAdminSerializer(req).data)
