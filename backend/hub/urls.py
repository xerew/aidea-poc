from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import CourseDetailView, CourseEnrollView, CoursesView, HomeView, LoginView, LogoutView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('courses/', CoursesView.as_view(), name='courses'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:pk>/enroll/', CourseEnrollView.as_view(), name='course-enroll'),
    path('home/', HomeView.as_view(), name='home'),
]
