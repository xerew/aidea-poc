from itertools import groupby

from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import OnboardingDimension, SelfEfficacyAttempt, SelfEfficacyConfig
from hub.views.permissions import IsAdmin


class AdminSelfEfficacyView(APIView):
    """GET/PATCH the retake switch. When open, teachers who already completed
    the assessment may take it again (each completion becomes a new attempt)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({'retake_open': SelfEfficacyConfig.get().retake_open})

    def patch(self, request):
        cfg = SelfEfficacyConfig.get()
        cfg.retake_open = bool(request.data.get('retake_open'))
        cfg.save(update_fields=['retake_open'])
        return Response({'retake_open': cfg.retake_open})


class AdminSelfEfficacyAttemptsView(APIView):
    """The attempt history for every teacher who has completed at least once,
    so admins can compare self-efficacy across attempts (e.g. pre/post)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        dimensions = list(OnboardingDimension.objects.filter(is_active=True).order_by('order'))
        attempts = (
            SelfEfficacyAttempt.objects
            .select_related('user')
            .order_by('user_id', 'created_at')
        )

        users = []
        for user_id, rows in groupby(attempts, key=lambda a: a.user_id):
            rows = list(rows)
            user = rows[0].user
            full_name = f'{user.first_name} {user.last_name}'.strip()
            users.append({
                'user_id': user_id,
                'name': full_name or user.username,
                'username': user.username,
                'attempts': [{
                    'created_at': a.created_at.isoformat(),
                    'overall_average': a.overall_average,
                    'overall_band': a.overall_band,
                    'competency_score': a.competency_score,
                    'dimensions': a.dimension_scores,
                } for a in rows],
            })
        # Most recently active teachers first.
        users.sort(key=lambda u: u['attempts'][-1]['created_at'], reverse=True)

        return Response({
            'dimensions': [{'slug': d.slug, 'name': d.name} for d in dimensions],
            'users': users,
        })
