from django.urls import path

from .views import (
    AnalyticsCourseTeachersView,
    AnalyticsExportView,
    AnalyticsOverviewView,
    CourseContentView,
    CourseLearnersView,
    CourseLearnerTimelineView,
)

urlpatterns = [
    path('overview/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
    path('export/', AnalyticsExportView.as_view(), name='analytics-export'),
    path('courses/<int:pk>/teachers/', AnalyticsCourseTeachersView.as_view(), name='analytics-course-teachers'),
    path('courses/<int:pk>/content/', CourseContentView.as_view(), name='analytics-course-content'),
    path('courses/<int:pk>/learners/', CourseLearnersView.as_view(), name='analytics-course-learners'),
    path('courses/<int:pk>/learners/<int:user_id>/', CourseLearnerTimelineView.as_view(), name='analytics-course-learner'),
]
