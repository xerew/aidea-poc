from .auth import LoginView, LogoutView, RegisterView
from .authoring_course import (
    AuthoringCourseDetailView,
    AuthoringCoursePublishView,
    AuthoringCoursesView,
    AuthoringPillarsView,
)
from .authoring_lesson import (
    AuthoringLessonDetailView,
    AuthoringLessonReorderView,
    AuthoringLessonView,
)
from .authoring_module import (
    AuthoringModuleDetailView,
    AuthoringModuleEditorView,
    AuthoringModuleReorderView,
    AuthoringModuleView,
)
from .learner import (
    CourseDetailView,
    CourseEnrollView,
    CourseLearnView,
    CoursesView,
    HomeView,
    LessonCompleteView,
    LessonDetailView,
    MyLearningView,
)
from .onboarding import OnboardingView
from .pathway import PathwayView
from .permissions import IsContentCreator, IsTeacher
from .profile import (
    ChangePasswordView,
    ProfilePersonalInfoView,
    ProfilePreferencesView,
    ProfileSettingsView,
)
from .recommendations import RecommendationEventView, RecommendationsView

__all__ = [
    'AuthoringCourseDetailView',
    'AuthoringCoursePublishView',
    'AuthoringCoursesView',
    'AuthoringLessonDetailView',
    'AuthoringLessonReorderView',
    'AuthoringLessonView',
    'AuthoringModuleDetailView',
    'AuthoringModuleEditorView',
    'AuthoringModuleReorderView',
    'AuthoringModuleView',
    'AuthoringPillarsView',
    'CourseDetailView',
    'CourseEnrollView',
    'CourseLearnView',
    'CoursesView',
    'HomeView',
    'MyLearningView',
    'LessonCompleteView',
    'LessonDetailView',
    'IsContentCreator',
    'IsTeacher',
    'LoginView',
    'LogoutView',
    'RegisterView',
    'OnboardingView',
    'PathwayView',
    'ChangePasswordView',
    'ProfilePersonalInfoView',
    'ProfilePreferencesView',
    'ProfileSettingsView',
    'RecommendationEventView',
    'RecommendationsView',
]
