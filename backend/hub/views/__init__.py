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
from .assignments import (
    AssignmentSubmitView,
    ReviewActionView,
    ReviewQueueView,
    SubmissionUploadView,
)
from .auth import LoginView, LogoutView, MeView, RegisterView
from .authoring_course import (
    AuthoringCourseDetailView,
    AuthoringCoursePublishView,
    AuthoringCoursesView,
    AuthoringCourseTranslateView,
    AuthoringCourseUnpublishView,
    AuthoringPillarsView,
    AuthoringTranslationReviewView,
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
from .feedback import (
    AdminFeedbackDetailView,
    AdminFeedbackListView,
    FeedbackMineView,
    FeedbackUploadView,
    FeedbackView,
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
from .messaging import (
    ConversationDetailView,
    ConversationListView,
    UnreadMessageCountView,
)
from .onboarding import OnboardingView, SelfEfficacyRetakeView, SelfEfficacyView
from .password_reset import PasswordResetConfirmView, PasswordResetRequestView
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
from .public_profile import PublicProfileView
from .recommendations import RecommendationEventView, RecommendationsView
from .self_efficacy_admin import AdminSelfEfficacyAttemptsView, AdminSelfEfficacyView
from .study import (
    AdminStudyExportView,
    AdminStudyView,
    StudyAssessmentView,
    StudyConsentView,
    StudyStatusView,
)
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
    'SubmissionUploadView',
    'AuthoringCourseDetailView',
    'AuthoringCourseExportView',
    'AuthoringCourseImportView',
    'AuthoringCourseTemplateView',
    'AuthoringCoursePublishView',
    'AuthoringCourseTranslateView',
    'AuthoringTranslationReviewView',
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
    'ConversationDetailView',
    'ConversationListView',
    'UnreadMessageCountView',
    'AdminFeedbackDetailView',
    'AdminFeedbackListView',
    'FeedbackMineView',
    'FeedbackUploadView',
    'FeedbackView',
    'OnboardingView',
    'SelfEfficacyView',
    'SelfEfficacyRetakeView',
    'AdminSelfEfficacyView',
    'AdminSelfEfficacyAttemptsView',
    'PasswordResetConfirmView',
    'PasswordResetRequestView',
    'PathwayView',
    'PreferenceQuizView',
    'PublicProfileView',
    'AdminStudyExportView',
    'AdminStudyView',
    'StudyAssessmentView',
    'StudyConsentView',
    'StudyStatusView',
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
