from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from .models import (
    AccessRequest,
    Course,
    CourseEditHistory,
    Enrollment,
    LearnerActivityConfig,
    LearningPath,
    LearningPathCourse,
    LearningPillar,
    Lesson,
    LessonProgress,
    LessonSession,
    Module,
    PreferenceOption,
    PreferenceQuestion,
    UserLearningPath,
    UserProfile,
)
from .models.recommendations import (
    CourseEmbedding,
    CourseRecommendation,
    CourseView,
    RecommendationConfig,
    RecommendationEvent,
)

# ── User + Profile ────────────────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'user_type', 'gender', 'country',
        'avatar_initials', 'competency_score', 'onboarding_completed',
        'subject_area', 'school', 'phone', 'location',
        'preferred_pillars', 'learning_style', 'weekly_learning_goal',
        'email_notifications', 'progress_reminders', 'profile_public', 'share_progress',
    ]
    readonly_fields = ['avatar_initials', 'competency_score']


class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'get_full_name', 'get_user_type', 'get_country', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__user_type', 'profile__country']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['username']

    @admin.display(description='Role', ordering='profile__user_type')
    def get_user_type(self, obj):
        if not hasattr(obj, 'profile'):
            return '—'
        colours = {'admin': '#dc2626', 'content_creator': '#7c3aed', 'teacher': '#2563eb'}
        labels = {'admin': 'Admin', 'content_creator': 'Content Creator', 'teacher': 'Teacher'}
        ut = obj.profile.user_type
        colour = colours.get(ut, '#6b7280')
        label = labels.get(ut, ut)
        return format_html('<span style="color:{};font-weight:600">{}</span>', colour, label)

    @admin.display(description='Country', ordering='profile__country')
    def get_country(self, obj):
        return getattr(obj, 'profile', None) and obj.profile.country or '—'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'get_username', 'get_email', 'user_type', 'gender', 'country', 'competency_score', 'onboarding_completed']
    list_filter  = ['user_type', 'gender', 'country', 'onboarding_completed']
    list_editable = ['user_type']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['avatar_initials', 'competency_score']
    fieldsets = [
        ('Identity', {'fields': ['user', 'user_type', 'avatar_initials', 'competency_score']}),
        ('Personal', {'fields': ['gender', 'country', 'subject_area', 'teaching_level', 'school', 'phone', 'location', 'goals']}),
        ('Learning', {'fields': ['preferred_pillars', 'learning_style', 'weekly_learning_goal', 'onboarding_completed']}),
        ('Notifications', {'fields': ['email_notifications', 'progress_reminders', 'profile_public', 'share_progress']}),
    ]

    @admin.display(description='Full Name', ordering='user__last_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or '—'

    @admin.display(description='Username', ordering='user__username')
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description='Email', ordering='user__email')
    def get_email(self, obj):
        return obj.user.email


# ── Preference quiz ───────────────────────────────────────────────────────────

class PreferenceOptionInline(admin.TabularInline):
    model = PreferenceOption
    extra = 2
    fields = ['text', 'maps_to', 'order']
    ordering = ['order']


@admin.register(PreferenceQuestion)
class PreferenceQuestionAdmin(admin.ModelAdmin):
    list_display  = ['text', 'order', 'is_active', 'option_count']
    list_editable = ['order', 'is_active']
    inlines = [PreferenceOptionInline]

    @admin.display(description='Options')
    def option_count(self, obj):
        return obj.options.count()


# ── Access Requests ───────────────────────────────────────────────────────────

@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display  = ['user', 'get_email', 'status_badge', 'created_at', 'reviewed_by', 'reviewed_at']
    list_filter   = ['status']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'message', 'created_at', 'reviewed_at', 'reviewed_by', 'denial_seen']
    ordering = ['-created_at']
    actions = ['approve_requests', 'deny_requests']

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {'pending': '#d97706', 'approved': '#16a34a', 'denied': '#dc2626'}
        colour = colours.get(obj.status, '#6b7280')
        return format_html('<span style="color:{};font-weight:600">{}</span>', colour, obj.get_status_display())

    @admin.action(description='Approve selected access requests')
    def approve_requests(self, request, queryset):
        pending = list(queryset.filter(status=AccessRequest.Status.PENDING))
        for req in pending:
            req.user.profile.user_type = UserProfile.UserType.CONTENT_CREATOR
            req.user.profile.save(update_fields=['user_type'])
            req.status = AccessRequest.Status.APPROVED
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save()
        self.message_user(request, f'{len(pending)} request(s) approved.', messages.SUCCESS)

    @admin.action(description='Deny selected access requests')
    def deny_requests(self, request, queryset):
        pending = queryset.filter(status=AccessRequest.Status.PENDING)
        count = pending.update(
            status=AccessRequest.Status.DENIED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'{count} request(s) denied.', messages.WARNING)


# ── Learning Pillars & Courses ────────────────────────────────────────────────

@admin.register(LearningPillar)
class LearningPillarAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order']


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ['title', 'order']
    ordering = ['order']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = ['title', 'pillar', 'level', 'content_format', 'is_published', 'created_by', 'created_at']
    list_filter   = ['pillar', 'is_published', 'level', 'content_format']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    inlines = [ModuleInline]
    actions = ['publish_courses', 'unpublish_courses']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Authorship drives editing rights in the app, so only content creators
        # make sense as authors; blank = "AIDEA team".
        if db_field.name == 'created_by':
            kwargs['queryset'] = User.objects.filter(
                profile__user_type=UserProfile.UserType.CONTENT_CREATOR,
            ).order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description='Publish selected courses')
    def publish_courses(self, request, queryset):
        count = queryset.filter(is_published=False).update(is_published=True)
        self.message_user(request, f'{count} course(s) published.')

    @admin.action(description='Unpublish selected courses')
    def unpublish_courses(self, request, queryset):
        count = queryset.filter(is_published=True).update(is_published=False)
        self.message_user(request, f'{count} course(s) unpublished.')


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'lesson_type', 'order', 'is_required']
    ordering = ['order']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display  = ['title', 'course', 'order']
    list_filter   = ['course__pillar', 'course']
    search_fields = ['title', 'course__title']
    ordering = ['course', 'order']
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'lesson_type', 'order', 'is_required']
    list_filter  = ['lesson_type', 'module__course__pillar']
    search_fields = ['title', 'module__title']
    ordering = ['module', 'order']


# ── Enrollments & Progress ────────────────────────────────────────────────────

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display    = ['user', 'course', 'progress_pct', 'current_module', 'enrolled_at', 'last_accessed_at']
    list_filter     = ['course__pillar', 'course']
    search_fields   = ['user__username', 'course__title']
    readonly_fields = ['enrolled_at', 'last_accessed_at', 'lesson_activity']

    @admin.display(description='Lesson Activity')
    def lesson_activity(self, obj):
        records = (
            LessonProgress.objects
            .filter(user=obj.user, lesson__module__course=obj.course)
            .select_related('lesson', 'lesson__module')
            .order_by('lesson__module__order', 'lesson__order')
        )
        if not records.exists():
            return 'No lessons completed yet.'
        rows = ''.join(
            '<tr>'
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.lesson.module.title}</td>'
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.lesson.title}</td>'
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.lesson.get_lesson_type_display()}</td>'
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{"required" if r.lesson.is_required else "optional"}</td>'
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.completed_at.strftime("%Y-%m-%d %H:%M UTC") if r.completed_at else "—"}</td>'
            '</tr>'
            for r in records
        )
        html = (
            '<table style="border-collapse:collapse;width:100%;font-size:13px">'
            '<thead><tr style="background:#f8f8f8;text-align:left">'
            '<th style="padding:6px 10px">Module</th>'
            '<th style="padding:6px 10px">Lesson</th>'
            '<th style="padding:6px 10px">Type</th>'
            '<th style="padding:6px 10px">Required</th>'
            '<th style="padding:6px 10px">Completed At</th>'
            '</tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
        return format_html('{}', mark_safe(html))  # noqa: S308


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'lesson', 'get_course', 'completed_at']
    list_filter   = ['lesson__module__course__pillar', 'lesson__module__course']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['user', 'lesson', 'completed_at']
    ordering = ['-completed_at']

    @admin.display(description='Course', ordering='lesson__module__course__title')
    def get_course(self, obj):
        return obj.lesson.module.course.title


# ── Learning Paths ────────────────────────────────────────────────────────────

class LearningPathCourseInline(admin.TabularInline):
    model = LearningPathCourse
    extra = 1
    fields = ['course', 'order']
    ordering = ['order']


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'competency_min', 'competency_max']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [LearningPathCourseInline]


@admin.register(UserLearningPath)
class UserLearningPathAdmin(admin.ModelAdmin):
    list_display  = ['user', 'path', 'assigned_at']
    list_filter   = ['path']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['assigned_at']
    ordering = ['-assigned_at']


# ── Course History ────────────────────────────────────────────────────────────

@admin.register(CourseEditHistory)
class CourseEditHistoryAdmin(admin.ModelAdmin):
    list_display    = ['course', 'editor', 'edited_at']
    list_filter     = ['course__pillar', 'editor']
    search_fields   = ['course__title', 'editor__username']
    readonly_fields = ['course', 'editor', 'edited_at', 'changes']
    ordering = ['-edited_at']


# ── Activity ──────────────────────────────────────────────────────────────────

@admin.register(LessonSession)
class LessonSessionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'lesson', 'started_at']
    list_filter     = ['lesson__lesson_type', 'lesson__module__course__pillar']
    search_fields   = ['user__username', 'lesson__title']
    readonly_fields = ['user', 'lesson', 'started_at']
    ordering = ['-started_at']


@admin.register(LearnerActivityConfig)
class LearnerActivityConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Quiz → Competency toggle', {'fields': ['quiz_affects_competency']}),
        ('Weights (active when toggle is on)', {'fields': ['quiz_pass_threshold', 'quiz_weight_pass', 'quiz_weight_fail']}),
    ]

    def has_add_permission(self, request):
        return not LearnerActivityConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ── Recommendations ───────────────────────────────────────────────────────────

@admin.register(RecommendationConfig)
class RecommendationConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Signal weights', {'fields': ['w_completed', 'w_deep', 'w_active', 'w_enrolled', 'w_abandoned', 'w_lesson', 'w_view']}),
        ('Blend weights', {'fields': ['alpha', 'beta', 'gamma', 'style_boost']}),
        ('Bandit config', {'fields': ['bandit_active', 'n_min', 'n_full', 'learning_rate', 'reward_click', 'reward_enroll', 'reward_complete']}),
    ]

    def has_add_permission(self, request):
        return not RecommendationConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecommendationEvent)
class RecommendationEventAdmin(admin.ModelAdmin):
    list_display    = ['user', 'course', 'event_type', 'source', 'rank', 'created_at']
    list_filter     = ['event_type', 'source']
    search_fields   = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'event_type', 'rank', 'source', 'weights_snapshot', 'created_at']
    ordering = ['-created_at']


@admin.register(CourseView)
class CourseViewAdmin(admin.ModelAdmin):
    list_display    = ['user', 'course', 'created_at']
    list_filter     = ['course__pillar']
    search_fields   = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'created_at']
    ordering = ['-created_at']


@admin.register(CourseRecommendation)
class CourseRecommendationAdmin(admin.ModelAdmin):
    list_display    = ['user', 'course', 'score', 'computed_at']
    list_filter     = ['course__pillar']
    search_fields   = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'score', 'computed_at']
    ordering = ['-score']


@admin.register(CourseEmbedding)
class CourseEmbeddingAdmin(admin.ModelAdmin):
    list_display  = ['course', 'computed_at']
    search_fields = ['course__title']
    readonly_fields = ['course', 'embedding', 'computed_at']
    ordering = ['course']
