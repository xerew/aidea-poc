from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, StudyConfig
from hub.models.pathway import UserLearningPath
from hub.serializers.pathway import UserLearningPathSerializer
from hub.study_logic import active_group
from hub.views.permissions import HasProfile


def _published(course_ids):
    return Course.objects.filter(id__in=course_ids or [], is_published=True).exists()


def _empty_reason(fixed):
    """Why a pathway has no courses, so the page can explain it."""
    if fixed:
        return 'study_curriculum_empty'   # the study's control curriculum has none published
    if not Course.objects.filter(is_published=True).exists():
        return 'no_published_courses'
    # The only exclusion in pathway_gen is level: courses more than one level
    # above the user's competency band.
    return 'above_level'


class PathwayView(APIView):
    """Every role gets a pathway the same way: by completing onboarding
    (subject, teaching level, role at school, goals), which assigns it."""
    permission_classes = [HasProfile]

    def get(self, request):
        user_path = (
            UserLearningPath.objects
            .select_related('path', 'user__profile')
            .filter(user=request.user)
            .first()
        )
        if user_path is None or not request.user.profile.onboarding_completed:
            return Response(
                {'detail': 'No pathway assigned. Complete onboarding first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Fixed-group participants follow the study's control curriculum instead
        # of their personalised pathway (the experimental manipulation).
        fixed = active_group(request.user) == 'fixed'
        if not fixed and not _published(user_path.course_ids):
            # Generated before any suitable course existed: try again now.
            from hub.pathway_gen import generate_pathway
            user_path.course_ids = generate_pathway(request.user)
            user_path.save(update_fields=['course_ids'])
        if fixed:
            control = StudyConfig.get().control_path
            if control:
                ordered = list(
                    control.path_courses.order_by('order').values_list('course_id', flat=True)
                )
                published = set(
                    Course.objects.filter(id__in=ordered, is_published=True).values_list('id', flat=True)
                )
                user_path.course_ids = [cid for cid in ordered if cid in published]
        serializer = UserLearningPathSerializer(
            user_path, context={'user': request.user, 'request': request},
        )
        data = serializer.data
        data['empty_reason'] = None if data['courses'] else _empty_reason(fixed)
        return Response(data)
