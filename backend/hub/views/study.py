from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import (
    Enrollment,
    LessonProgress,
    LessonSession,
    StudyAssessmentOption,
    StudyAssessmentQuestion,
    StudyConfig,
    StudyParticipant,
    StudyPreregistration,
    UserProfile,
)
from hub.study_logic import assign_group
from hub.study_stats import compute_study_results

from .permissions import IsAdmin


def _is_teacher(user):
    return getattr(getattr(user, 'profile', None), 'user_type', None) == UserProfile.UserType.TEACHER


def _participant(user):
    # Explicit query (not the cached reverse relation) so state is always fresh.
    return StudyParticipant.objects.filter(user=user).first()


def _phase_for(participant, config):
    """Which assessment (if any) the participant should take now."""
    if participant is None or not participant.in_study:
        return None
    if participant.pre_score is None:
        return 'pre'
    if config.post_test_open and participant.post_score is None:
        return 'post'
    return None


class StudyStatusView(APIView):
    """GET /api/study/status/ — what the frontend needs to drive the study UX."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = StudyConfig.get()
        participant = _participant(request.user)
        has_assessment = StudyAssessmentQuestion.objects.exists()
        phase = _phase_for(participant, config)

        return Response({
            'enabled': config.enabled,
            'is_teacher': _is_teacher(request.user),
            'responded': participant is not None,          # consented or declined already
            'in_study': bool(participant and participant.in_study),
            'group': participant.group if participant else '',
            'has_assessment': has_assessment,
            'pre_done': bool(participant and participant.pre_score is not None),
            'post_done': bool(participant and participant.post_score is not None),
            'needs_consent': config.enabled and _is_teacher(request.user) and participant is None,
            'pending_phase': phase,                        # 'pre' | 'post' | None
        })


class StudyConsentView(APIView):
    """POST /api/study/consent/ {consent: bool} — join or decline the study."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        config = StudyConfig.get()
        if not config.enabled:
            return Response({'detail': 'No active study.'}, status=status.HTTP_400_BAD_REQUEST)
        if not _is_teacher(request.user):
            return Response({'detail': 'Only teachers can join the study.'}, status=status.HTTP_403_FORBIDDEN)
        if StudyParticipant.objects.filter(user=request.user).exists():
            return Response({'detail': 'Already responded.'}, status=status.HTTP_400_BAD_REQUEST)

        consent = bool(request.data.get('consent'))
        if consent:
            StudyParticipant.objects.create(
                user=request.user, in_study=True, group=assign_group(),
                consented_at=timezone.now(),
            )
        else:
            StudyParticipant.objects.create(user=request.user, in_study=False)
        return Response({'status': 'ok', 'consent': consent}, status=status.HTTP_201_CREATED)


class StudyAssessmentView(APIView):
    """GET  /api/study/assessment/ — questions for the phase due now (no answers).
       POST /api/study/assessment/ {phase, answers:{qid:optionId}} — score & store."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = StudyConfig.get()
        participant = _participant(request.user)
        phase = _phase_for(participant, config)
        if phase is None:
            return Response({'detail': 'No assessment due.'}, status=status.HTTP_400_BAD_REQUEST)

        questions = StudyAssessmentQuestion.objects.prefetch_related('options').all()
        return Response({
            'phase': phase,
            'questions': [
                {
                    'id': q.id,
                    'text': q.text,
                    'options': [{'id': o.id, 'text': o.text} for o in q.options.all()],
                }
                for q in questions
            ],
        })

    def post(self, request):
        config = StudyConfig.get()
        participant = _participant(request.user)
        if participant is None or not participant.in_study:
            return Response({'detail': 'Not a study participant.'}, status=status.HTTP_403_FORBIDDEN)

        phase = request.data.get('phase')
        if phase == 'pre':
            if participant.pre_score is not None:
                return Response({'detail': 'Pre-test already completed.'}, status=status.HTTP_400_BAD_REQUEST)
        elif phase == 'post':
            if participant.pre_score is None:
                return Response({'detail': 'Complete the pre-test first.'}, status=status.HTTP_400_BAD_REQUEST)
            if not config.post_test_open:
                return Response({'detail': 'The post-test is not open yet.'}, status=status.HTTP_400_BAD_REQUEST)
            if participant.post_score is not None:
                return Response({'detail': 'Post-test already completed.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'detail': "phase must be 'pre' or 'post'."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get('answers') or {}
        if not isinstance(answers, dict):
            return Response({'detail': 'answers must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

        # Score = number of questions answered with the correct option.
        correct_ids = set(
            StudyAssessmentOption.objects.filter(is_correct=True).values_list('id', flat=True)
        )
        score = sum(1 for oid in answers.values() if _as_int(oid) in correct_ids)

        now = timezone.now()
        if phase == 'pre':
            participant.pre_score = score
            participant.pre_completed_at = now
            participant.save(update_fields=['pre_score', 'pre_completed_at'])
        else:
            participant.post_score = score
            participant.post_completed_at = now
            participant.save(update_fields=['post_score', 'post_completed_at'])

        return Response({'phase': phase, 'score': score})


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ── Admin (researcher) ────────────────────────────────────────────────────────

class AdminStudyView(APIView):
    """GET/PATCH /api/admin/study/ — study config + participant summary."""
    permission_classes = [IsAdmin]

    def _payload(self):
        from hub.models import LearningPath
        config = StudyConfig.get()
        participants = StudyParticipant.objects.all()
        in_study = participants.filter(in_study=True)
        return {
            'enabled': config.enabled,
            'post_test_open': config.post_test_open,
            'control_path': config.control_path_id,
            'control_path_name': config.control_path.name if config.control_path else '',
            'available_paths': [{'id': p.id, 'name': p.name} for p in LearningPath.objects.all()],
            'has_assessment': StudyAssessmentQuestion.objects.exists(),
            'assessment_questions': StudyAssessmentQuestion.objects.count(),
            'counts': {
                'total': participants.count(),
                'adaptive': in_study.filter(group=StudyParticipant.Group.ADAPTIVE).count(),
                'fixed': in_study.filter(group=StudyParticipant.Group.FIXED).count(),
                'declined': participants.filter(in_study=False).count(),
                'pre_done': in_study.exclude(pre_score=None).count(),
                'post_done': in_study.exclude(post_score=None).count(),
            },
        }

    def get(self, request):
        return Response(self._payload())

    def patch(self, request):
        from hub.models import LearningPath
        config = StudyConfig.get()
        if 'enabled' in request.data:
            config.enabled = bool(request.data['enabled'])
        if 'post_test_open' in request.data:
            config.post_test_open = bool(request.data['post_test_open'])
        if 'control_path' in request.data:
            pid = request.data['control_path']
            if pid in (None, ''):
                config.control_path = None
            else:
                try:
                    config.control_path = LearningPath.objects.get(pk=pid)
                except LearningPath.DoesNotExist:
                    return Response({'detail': 'Unknown learning path.'}, status=status.HTTP_400_BAD_REQUEST)
        config.save()
        return Response(self._payload())


class AdminStudyExportView(APIView):
    """GET /api/admin/study/export/ — pseudonymised participant data as XLSX."""
    permission_classes = [IsAdmin]

    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Participants'
        ws.append([
            'participant', 'group', 'consented_at', 'pre_score', 'post_score', 'gain',
            'courses_completed', 'lessons_completed', 'total_time_min', 'avg_quiz_score',
            'days_active', 'pre_at', 'post_at',
        ])

        def _dt(value):
            return value.strftime('%Y-%m-%d %H:%M') if value else ''

        participants = StudyParticipant.objects.filter(in_study=True).select_related('user')
        for i, p in enumerate(participants, start=1):
            u = p.user
            progress = list(LessonProgress.objects.filter(user=u))
            times = [lp.time_spent_seconds for lp in progress if lp.time_spent_seconds]
            quizzes = [lp.quiz_score for lp in progress if lp.quiz_score is not None]
            days_active = LessonSession.objects.filter(user=u).dates('started_at', 'day').count()
            ws.append([
                f'P{i:04d}',
                p.group,
                _dt(p.consented_at),
                p.pre_score if p.pre_score is not None else '',
                p.post_score if p.post_score is not None else '',
                p.gain if p.gain is not None else '',
                Enrollment.objects.filter(user=u, progress_pct=100).count(),
                sum(1 for lp in progress if lp.completed_at is not None),
                round(sum(times) / 60, 1) if times else 0,
                round(sum(quizzes) / len(quizzes), 3) if quizzes else '',
                days_active,
                _dt(p.pre_completed_at),
                _dt(p.post_completed_at),
            ])

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="aidea-study-export.xlsx"'
        return response


def _design_snapshot():
    """Canonical snapshot of the current study design, for pre-registration and
    change detection."""
    config = StudyConfig.get()
    questions = []
    for q in StudyAssessmentQuestion.objects.prefetch_related('options').order_by('order', 'id'):
        questions.append({
            'id': q.id,
            'text': q.text,
            'options': [
                {'id': o.id, 'text': o.text, 'is_correct': o.is_correct}
                for o in q.options.all().order_by('order', 'id')
            ],
        })
    return {
        'enabled': config.enabled,
        'control_path_id': config.control_path_id,
        'questions': questions,
    }


class AdminStudyStatsView(APIView):
    """GET → CONSORT counts, per-group descriptives, gain t-test + Cohen's d and
    the pre-score-adjusted ANCOVA for the adaptive-vs-fixed comparison."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(compute_study_results(StudyParticipant.objects.all()))


class AdminStudyPreregistrationView(APIView):
    """GET  → hypothesis, lock timestamp, and whether the design changed since.
       PATCH {hypothesis} → save the hypothesis (draft, does not lock).
       POST  → lock: snapshot the current design with a timestamp."""
    permission_classes = [IsAdmin]

    def _payload(self, prereg):
        changed = bool(prereg.locked_at) and prereg.snapshot != _design_snapshot()
        return {
            'hypothesis': prereg.hypothesis,
            'locked_at': prereg.locked_at.isoformat() if prereg.locked_at else None,
            'changed_since_lock': changed,
        }

    def get(self, request):
        return Response(self._payload(StudyPreregistration.get()))

    def patch(self, request):
        prereg = StudyPreregistration.get()
        prereg.hypothesis = str(request.data.get('hypothesis') or '').strip()
        prereg.save(update_fields=['hypothesis'])
        return Response(self._payload(prereg))

    def post(self, request):
        prereg = StudyPreregistration.get()
        if 'hypothesis' in request.data:
            prereg.hypothesis = str(request.data.get('hypothesis') or '').strip()
        prereg.snapshot = _design_snapshot()
        prereg.locked_at = timezone.now()
        prereg.save()
        return Response(self._payload(prereg))
