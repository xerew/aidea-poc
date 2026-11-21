"""Admin-only: one person's activity across the platform (spec 2026-11-21)."""
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.user_activity import CATEGORIES, authoring_rows, course_rows, feed, login_rows, summary
from hub.views.permissions import IsAdmin


def _user_or_404(pk):
    user = User.objects.select_related('profile').filter(pk=pk).first()
    if user is None:
        return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    return user, None


class AdminUserActivityView(APIView):
    """GET — summary, courses, authoring, logins and the first feed page."""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        user, failure = _user_or_404(pk)
        if failure:
            return failure
        items, next_before = feed(user)
        return Response({
            'summary': summary(user), 'courses': course_rows(user), 'authoring': authoring_rows(user),
            'logins': login_rows(user), 'feed': items, 'next_before': next_before,
        })


class AdminUserActivityFeedView(APIView):
    """GET ?before=<ISO>&category=<…> — the next feed page."""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        user, failure = _user_or_404(pk)
        if failure:
            return failure
        before = request.query_params.get('before')
        if before:
            before = parse_datetime(before)
            if before is None:
                return Response({'detail': 'Invalid before.'}, status=status.HTTP_400_BAD_REQUEST)
        category = request.query_params.get('category') or None
        if category is not None and category not in CATEGORIES:
            return Response({'detail': 'Unknown category.'}, status=status.HTTP_400_BAD_REQUEST)
        items, next_before = feed(user, before=before or None, category=category)
        return Response({'items': items, 'next_before': next_before})


class AdminUserActivityExportView(APIView):
    """GET — everything on the page (the complete feed) as <username>-activity.xlsx."""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        from analytics.views import _xlsx_response
        from hub.user_activity_workbook import build_user_workbook
        user, failure = _user_or_404(pk)
        if failure:
            return failure
        return _xlsx_response(build_user_workbook(user), f'{user.username}-activity.xlsx')
