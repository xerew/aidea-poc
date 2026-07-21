from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Course, CourseEditHistory, LearningPillar
from hub.serializers import CourseAuthoringSerializer, PillarSerializer
from hub.translation import LANGUAGE_NAMES

from .permissions import IsContentCreator, can_edit_published


class AuthoringPillarsView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request):
        return Response(PillarSerializer(LearningPillar.objects.all(), many=True).data)


class AuthoringCoursesView(APIView):
    permission_classes = [IsContentCreator]

    def get(self, request):
        qs = (
            Course.objects
            .select_related('pillar', 'created_by')
            .prefetch_related('modules')
            .order_by('pillar__order', 'title')
        )
        return Response(CourseAuthoringSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CourseAuthoringSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save(created_by=request.user)
        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'course_created': {'title': course.title}},
        )
        return Response(CourseAuthoringSerializer(course).data, status=status.HTTP_201_CREATED)


class AuthoringCourseDetailView(APIView):
    permission_classes = [IsContentCreator]

    def _get_course(self, pk):
        try:
            return Course.objects.prefetch_related('modules').select_related('pillar').get(pk=pk)
        except Course.DoesNotExist:
            return None

    def get(self, request, pk):
        course = self._get_course(pk)
        if not course:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CourseAuthoringSerializer(course).data)

    def patch(self, request, pk):
        course = self._get_course(pk)
        if not course:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published and not can_edit_published(request.user, course):
            return Response(
                {'detail': 'Published courses can only be edited by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CourseAuthoringSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        changes = {}
        for field in ['title', 'description', 'level', 'duration_hours', 'learning_outcomes']:
            if field in serializer.validated_data:
                old_val = getattr(course, field)
                new_val = serializer.validated_data[field]
                if old_val != new_val:
                    changes[field] = {'old': old_val, 'new': new_val}
        if 'pillar' in serializer.validated_data:
            new_pillar = serializer.validated_data['pillar']
            if course.pillar_id != new_pillar.id:
                changes['pillar'] = {'old': course.pillar.name, 'new': new_pillar.name}

        serializer.save()

        if changes:
            CourseEditHistory.objects.create(course=course, editor=request.user, changes=changes)

        course.refresh_from_db()
        return Response(CourseAuthoringSerializer(course).data)


class AuthoringCoursePublishView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published:
            return Response({'detail': 'Course is already published.'}, status=status.HTTP_400_BAD_REQUEST)

        course.is_published = True
        course.save()
        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'course_published': {'title': course.title}},
        )
        return Response(CourseAuthoringSerializer(course).data)


class AuthoringCourseUnpublishView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not course.is_published:
            return Response({'detail': 'Course is not published.'}, status=status.HTTP_400_BAD_REQUEST)
        if not can_edit_published(request.user, course):
            return Response(
                {'detail': 'Published courses can only be unpublished by their author.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        course.is_published = False
        course.save()
        CourseEditHistory.objects.create(
            course=course,
            editor=request.user,
            changes={'course_unpublished': {'title': course.title}},
        )
        return Response(CourseAuthoringSerializer(course).data)


class AuthoringCourseTranslateView(APIView):
    permission_classes = [IsContentCreator]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if course.is_published and not can_edit_published(request.user, course):
            return Response({'detail': 'Only the author can translate this course.'},
                            status=status.HTTP_403_FORBIDDEN)
        language = request.data.get('language')
        valid = set(LANGUAGE_NAMES) - {course.source_language}
        if language not in valid:
            return Response({'detail': 'Invalid or source language.'}, status=status.HTTP_400_BAD_REQUEST)
        course.translation_status[language] = 'pending'
        course.save(update_fields=['translation_status'])
        from hub.tasks import translate_course
        translate_course.delay(course.id, language)
        return Response({'translation_status': course.translation_status}, status=status.HTTP_202_ACCEPTED)
