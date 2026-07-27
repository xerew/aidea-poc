from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, StudyConfig
from hub.models.pathway import UserLearningPath
from hub.serializers.pathway import UserLearningPathSerializer
from hub.study_logic import active_group
from hub.views.permissions import IsTeacher


class PathwayView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            user_path = (
                UserLearningPath.objects
                .select_related('path', 'user__profile')
                .get(user=request.user)
            )
        except UserLearningPath.DoesNotExist:
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
