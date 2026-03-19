from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Course, Enrollment, LearningPillar
from .serializers import (
    AideaTokenObtainPairSerializer,
    ContinueLearningSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    PillarSummarySerializer,
)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AideaTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out.'})


class CoursesView(APIView):
    def get(self, request):
        qs = Course.objects.select_related('pillar').prefetch_related('modules')
        pillar = request.query_params.get('pillar')
        level  = request.query_params.get('level')
        search = request.query_params.get('search')
        if pillar:
            qs = qs.filter(pillar__slug=pillar)
        if level:
            qs = qs.filter(level=level)
        if search:
            qs = qs.filter(title__icontains=search)
        serializer = CourseListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class CourseDetailView(APIView):
    def get(self, request, pk):
        try:
            course = Course.objects.prefetch_related('modules').select_related('pillar').get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseDetailSerializer(course, context={'request': request})
        return Response(serializer.data)


class CourseEnrollView(APIView):
    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
        )
        return Response(
            {'enrolled': True, 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class HomeView(APIView):
    def get(self, request):
        # Most recently accessed enrollment for "Continue Learning"
        latest_enrollment = (
            Enrollment.objects
            .filter(user=request.user)
            .select_related('course', 'current_module')
            .first()
        )

        continue_learning = (
            ContinueLearningSerializer(latest_enrollment).data
            if latest_enrollment else None
        )

        pillars = LearningPillar.objects.all()
        pillars_data = PillarSummarySerializer(
            pillars, many=True, context={'request': request}
        ).data

        return Response({
            'continue_learning': continue_learning,
            'pillars': pillars_data,
        })
