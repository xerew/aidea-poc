from django.urls import path

from .views import (
    AnalyticsCourseTeachersView,
    AnalyticsExportView,
    AnalyticsOverviewView,
)

urlpatterns = [
    path('overview/', AnalyticsOverviewView.as_view(), name='analytics-overview'),
    path('export/', AnalyticsExportView.as_view(), name='analytics-export'),
    path('courses/<int:pk>/teachers/', AnalyticsCourseTeachersView.as_view(), name='analytics-course-teachers'),
]
