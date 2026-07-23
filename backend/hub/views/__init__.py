from .access_requests import (
    AccessRequestDetailView,
    AccessRequestMineView,
    AccessRequestSeenView,
    AccessRequestView,
)
from .admin import (
    AdminAccessRequestListView,
    AdminAccessRequestReviewView,
    AdminRecomputeRecommendationsView,
    AdminUserListView,
    AdminUserRoleView,
)
from .assignments import AssignmentSubmitView, ReviewActionView, ReviewQueueView
from .auth import LoginView, LogoutView, MeView, RegisterView
from .authoring_course import (
    AuthoringCourseDetailView,
    AuthoringCoursePublishView,
    AuthoringCoursesView,
    AuthoringCourseTranslateView,
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
from .authoring_upload import AuthoringUploadView
from .authoring_xlsx import (
    AuthoringCourseExportView,
    AuthoringCourseImportView,
    AuthoringCourseTemplateView,
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
    QuizCheckView,
)
from .onboarding import OnboardingView
from .pathway import PathwayView
from .permissions import IsContentCreator, IsReviewer, IsTeacher
from .preference_quiz import PreferenceQuizView
from .profile import (
    ChangePasswordView,
    ProfileAvatarView,
    ProfileLanguageView,
    ProfilePersonalInfoView,
    ProfilePreferencesView,
    ProfileSettingsView,
)
from .recommendations import RecommendationEventView, RecommendationsView
from .subjects import SubjectsView

__all__ = [
    'AccessRequestDetailView',
    'AccessRequestMineView',
    'AccessRequestSeenView',
    'AccessRequestView',
    'AdminAccessRequestListView',
    'AdminRecomputeRecommendationsView',
    'AdminAccessRequestReviewView',
    'AdminUserListView',
    'AdminUserRoleView',
    'AssignmentSubmitView',
    'ReviewActionView',
    'ReviewQueueView',
    'AuthoringCourseDetailView',
    'AuthoringCourseExportView',
    'AuthoringCourseImportView',
    'AuthoringCourseTemplateView',
    'AuthoringCoursePublishView',
    'AuthoringCourseTranslateView',
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
    'AuthoringUploadView',
    'CourseDetailView',
    'CourseEnrollView',
    'CourseLearnView',
    'CoursesView',
    'HomeView',
    'MyLearningView',
    'LessonCompleteView',
    'LessonDetailView',
    'QuizCheckView',
    'IsContentCreator',
    'IsReviewer',
    'IsTeacher',
    'LoginView',
    'LogoutView',
    'MeView',
    'RegisterView',
    'OnboardingView',
    'PathwayView',
    'PreferenceQuizView',
    'SubjectsView',
    'ChangePasswordView',
    'ProfileAvatarView',
    'ProfileLanguageView',
    'ProfilePersonalInfoView',
    'ProfilePreferencesView',
    'ProfileSettingsView',
    'RecommendationEventView',
    'RecommendationsView',
]
