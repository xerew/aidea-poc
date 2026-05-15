from django.contrib import admin
from django.utils.html import format_html, mark_safe

from .models import (
    Course,
    CourseEditHistory,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    UserProfile,
)
from .models.recommendations import CourseView, RecommendationConfig, RecommendationEvent


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'avatar_initials']
    list_filter = ['user_type']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']


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
    list_display = ['title', 'pillar', 'level', 'content_format', 'is_published']
    list_filter = ['pillar', 'is_published', 'content_format']
    search_fields = ['title']
    inlines = [ModuleInline]


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'lesson_type', 'order', 'is_required']
    ordering = ['order']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course__pillar', 'course']
    search_fields = ['title', 'course__title']
    ordering = ['course', 'order']
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'lesson_type', 'order', 'is_required']
    list_filter = ['lesson_type', 'module__course__pillar']
    search_fields = ['title', 'module__title']
    ordering = ['module', 'order']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'progress_pct', 'current_module', 'enrolled_at', 'last_accessed_at']
    list_filter = ['course__pillar', 'course']
    search_fields = ['user__username', 'course__title']
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
            f'<td style="padding:4px 10px;border-bottom:1px solid #eee">{r.completed_at.strftime("%Y-%m-%d %H:%M UTC")}</td>'
            '</tr>'
            for r in records
        )
        html = (
            '<table style="border-collapse:collapse;width:100%;font-size:13px">'
            '<thead>'
            '<tr style="background:#f8f8f8;text-align:left">'
            '<th style="padding:6px 10px">Module</th>'
            '<th style="padding:6px 10px">Lesson</th>'
            '<th style="padding:6px 10px">Type</th>'
            '<th style="padding:6px 10px">Required</th>'
            '<th style="padding:6px 10px">Completed At</th>'
            '</tr>'
            '</thead>'
            f'<tbody>{rows}</tbody>'
            '</table>'
        )
        return format_html('{}', mark_safe(html))  # noqa: S308


@admin.register(CourseEditHistory)
class CourseEditHistoryAdmin(admin.ModelAdmin):
    list_display = ['course', 'editor', 'edited_at']
    list_filter = ['course__pillar', 'editor']
    search_fields = ['course__title', 'editor__username']
    readonly_fields = ['course', 'editor', 'edited_at', 'changes']
    ordering = ['-edited_at']


@admin.register(RecommendationConfig)
class RecommendationConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Signal weights', {
            'fields': ['w_completed', 'w_deep', 'w_active', 'w_enrolled', 'w_abandoned', 'w_lesson', 'w_view'],
        }),
        ('Blend weights', {
            'fields': ['alpha', 'beta', 'gamma', 'style_boost'],
        }),
        ('Bandit config', {
            'fields': ['bandit_active', 'n_min', 'n_full', 'learning_rate',
                       'reward_click', 'reward_enroll', 'reward_complete'],
        }),
    ]

    def has_add_permission(self, request):
        return not RecommendationConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecommendationEvent)
class RecommendationEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'event_type', 'source', 'rank', 'created_at']
    list_filter = ['event_type', 'source']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'event_type', 'rank', 'source', 'weights_snapshot', 'created_at']
    ordering = ['-created_at']


@admin.register(CourseView)
class CourseViewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'created_at']
    list_filter = ['course__pillar']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['user', 'course', 'created_at']
    ordering = ['-created_at']
