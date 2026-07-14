from .access_requests import (
    AccessRequestDetailView,
    AccessRequestMineView,
    AccessRequestSeenView,
    AccessRequestView,
)
from .admin import (
    AdminAccessRequestListView,
    AdminAccessRequestReviewView,
    AdminUserListView,
    AdminUserRoleView,
)
from .auth import LoginView, LogoutView, MeView, RegisterView
from .authoring_course import (
    AuthoringCourseDetailView,
    AuthoringCoursePublishView,
    AuthoringCoursesView,
    AuthoringCourseUnpublishView,
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
    ProfileAvatarView,
    ProfilePersonalInfoView,
    ProfilePreferencesView,
    ProfileSettingsView,
)
from .recommendations import RecommendationEventView, RecommendationsView

__all__ = [
    'AccessRequestDetailView',
    'AccessRequestMineView',
    'AccessRequestSeenView',
    'AccessRequestView',
    'AdminAccessRequestListView',
    'AdminAccessRequestReviewView',
    'AdminUserListView',
    'AdminUserRoleView',
    'AuthoringCourseDetailView',
    'AuthoringCoursePublishView',
    'AuthoringCourseUnpublishView',
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
    'MeView',
    'RegisterView',
    'OnboardingView',
    'PathwayView',
    'ChangePasswordView',
    'ProfileAvatarView',
    'ProfilePersonalInfoView',
    'ProfilePreferencesView',
    'ProfileSettingsView',
    'RecommendationEventView',
    'RecommendationsView',
]
