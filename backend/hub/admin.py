from django.contrib import admin

from .models import Course, CourseEditHistory, Enrollment, LearningPillar, Module, UserProfile


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
    list_display = ['title', 'pillar', 'is_published']
    list_filter = ['pillar', 'is_published']
    search_fields = ['title']
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course__pillar', 'course']
    search_fields = ['title', 'course__title']
    ordering = ['course', 'order']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'progress_pct', 'current_module', 'last_accessed_at']
    list_filter = ['course__pillar', 'course']
    search_fields = ['user__username', 'course__title']
    readonly_fields = ['enrolled_at', 'last_accessed_at']


@admin.register(CourseEditHistory)
class CourseEditHistoryAdmin(admin.ModelAdmin):
    list_display = ['course', 'editor', 'edited_at']
    list_filter = ['course__pillar', 'editor']
    search_fields = ['course__title', 'editor__username']
    readonly_fields = ['course', 'editor', 'edited_at', 'changes']
    ordering = ['-edited_at']
