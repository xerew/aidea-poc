from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, StudyConfig, UserProfile
from hub.models.pathway import LearningPath, UserLearningPath
from hub.serializers.pathway import UserLearningPathSerializer
from hub.study_logic import active_group
from hub.views.permissions import HasProfile


def _staff_pathway(user):
    """Content creators, AIDEA partners and admins never go through teacher
    onboarding (which assigns the pathway), so give them one on first visit,
    placed by their competency score like a teacher's."""
    from hub.pathway_gen import generate_pathway
    from hub.views.onboarding import assign_path
    try:
        path = assign_path(user.profile.competency_score)
    except LearningPath.DoesNotExist:
        return None
    user_path, _ = UserLearningPath.objects.get_or_create(
        user=user, defaults={'path': path, 'course_ids': generate_pathway(user)},
    )
    return user_path


class PathwayView(APIView):
    permission_classes = [HasProfile]

    def get(self, request):
        user_path = (
            UserLearningPath.objects
            .select_related('path', 'user__profile')
            .filter(user=request.user)
            .first()
        )
        if user_path is None and request.user.profile.user_type != UserProfile.UserType.TEACHER:
            user_path = _staff_pathway(request.user)
        if user_path is None:
            return Response(
                {'detail': 'No pathway assigned. Complete onboarding first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Fixed-group participants follow the study's control curriculum instead
        # of their personalised pathway (the experimental manipulation).
        if active_group(request.user) == 'fixed':
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
        return Response(serializer.data)
