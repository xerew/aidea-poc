import copy

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from hub.models import (
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    Subject,
    UserProfile,
)

from .seed_data import cohort as cohort_data
from .seed_data import pillar_teach_about_ai, pillar_teach_for_ai, pillar_teach_with_ai
from .seed_data.pathways import seed_pathways
from .seed_data.preference_quiz import seed_preference_quiz

PILLARS = [
    pillar_teach_with_ai.PILLAR,
    pillar_teach_for_ai.PILLAR,
    pillar_teach_about_ai.PILLAR,
]

# Subjects rotated across the demo teacher cohort so recommendations,
# analytics and CF peer-matching have some variety to work with.
COHORT_SUBJECT_SLUGS = [
    'mathematics', 'physics', 'biology', 'history',
    'languages', 'computer-science', 'arts', 'geography',
]


class Command(BaseCommand):
    help = 'Seed the database with learning pillars, courses, modules, lessons, and demo users.'

    def handle(self, *args, **options):
        # Subjects are created by migration 0026; cache them for tagging below.
        self.subjects = {s.slug: s for s in Subject.objects.all()}
        self._seed_pillars()
        seed_pathways()
        seed_preference_quiz()
        self._seed_demo_user()
        creator = self._seed_demo_content_creator()
        self._seed_demo_partner()
        self._assign_creator_courses(creator)
        self._seed_teacher_cohort(creator)
        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))

    def _seed_pillars(self):
        for pillar_data in copy.deepcopy(PILLARS):
            courses_data = pillar_data.pop('courses')
            pillar, created = LearningPillar.objects.update_or_create(
                slug=pillar_data['slug'],
                defaults=pillar_data,
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action} pillar: {pillar.name}')

            for course_data in courses_data:
                modules_data = course_data.pop('modules')
                course, _ = Course.objects.update_or_create(
                    title=course_data['title'],
                    pillar=pillar,
                    defaults={
                        'description':       course_data['description'],
                        'level':             course_data.get('level', 'beginner'),
                        'duration_hours':    course_data.get('duration_hours', 0),
                        'learning_outcomes': course_data.get('learning_outcomes', []),
                        'is_published':      True,
                    },
                )
                # These are AI-pedagogy courses relevant to any teacher, so tag
                # them General/All. Creators can narrow this per course in the UI.
                general = self.subjects.get('general')
                if general:
                    course.subjects.set([general])
                total_lessons = 0
                for order, module_data in enumerate(modules_data, start=1):
                    lessons_data = module_data.pop('lessons', [])
                    module, _ = Module.objects.update_or_create(
                        title=module_data['title'],
                        course=course,
                        defaults={
                            'order':            order,
                            'description':      module_data['description'],
                            'duration_minutes': module_data['duration_minutes'],
                        },
                    )
                    for lesson_order, lesson in enumerate(lessons_data, start=1):
                        Lesson.objects.update_or_create(
                            title=lesson['title'],
                            module=module,
                            defaults={
                                'lesson_type':      lesson['type'],
                                'order':            lesson_order,
                                'duration_minutes': lesson['duration'],
                                'is_required':      lesson['required'],
                                'content':          lesson.get('content', ''),
                                'quiz_data':        lesson.get('quiz_data', []),
                            },
                        )
                    total_lessons += len(lessons_data)

                self.stdout.write(
                    f'    Course: {course.title} ({len(modules_data)} modules, {total_lessons} lessons)'
                )

    def _seed_demo_user(self):
        user, created = User.objects.get_or_create(
            username='demo_teacher',
            defaults={
                'first_name': 'Nikos',
                'last_name': 'Grammatikos',
                'email': 'nikos@aidea.example.com',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': UserProfile.UserType.TEACHER,
                'avatar_initials': 'NG',
                'subject': self.subjects.get('mathematics'),
                'onboarding_completed': True,
                'competency_score': 3,
                'preferred_pillars': ['teach-with-ai'],
                'goals': ['save_time'],
            },
        )
        self._assign_demo_pathway(user)

        course = Course.objects.filter(pillar__slug='teach-with-ai').first()
        if course:
            module = course.modules.filter(order=2).first()
            Enrollment.objects.update_or_create(
                user=user,
                course=course,
                defaults={
                    'current_module': module,
                    'progress_pct': 65,
                },
            )
            self.stdout.write(f'  Demo user enrolled in: {course.title}')

        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Demo user ({action}): demo_teacher / demo1234')

    def _assign_demo_pathway(self, user):
        from hub.models import LearningPath, UserLearningPath
        from hub.pathway_gen import generate_pathway
        user.refresh_from_db()
        score = user.profile.competency_score
        path = (
            LearningPath.objects.filter(competency_min__lte=score, competency_max__gte=score).first()
            or LearningPath.objects.filter(slug='beginner-foundations').first()
        )
        if path:
            UserLearningPath.objects.update_or_create(
                user=user,
                defaults={'path': path, 'course_ids': generate_pathway(user)},
            )

    def _seed_demo_content_creator(self):
        user, created = User.objects.get_or_create(
            username='demo_creator',
            defaults={
                'first_name': 'Maria',
                'last_name': 'Papadaki',
                'email': 'maria@aidea.example.com',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': UserProfile.UserType.CONTENT_CREATOR,
                'avatar_initials': 'MP',
            },
        )

        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Demo content creator ({action}): demo_creator / demo1234')
        return user

    def _seed_demo_partner(self):
        user, created = User.objects.get_or_create(
            username='demo_partner',
            defaults={
                'first_name': 'Elena',
                'last_name': 'Kostopoulou',
                'email': 'elena@aidea.example.com',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': UserProfile.UserType.AIDEA_PARTNER,
                'avatar_initials': 'EK',
            },
        )

        action = 'Created' if created else 'Already exists'
        self.stdout.write(f'  Demo AIDEA partner ({action}): demo_partner / demo1234')
        return user

    def _assign_creator_courses(self, creator):
        updated = 0
        for title in cohort_data.CREATOR_COURSE_TITLES:
            updated += Course.objects.filter(title=title, created_by__isnull=True).update(created_by=creator)
        self.stdout.write(f'  Assigned {updated} course(s) to demo_creator')

    def _enroll_at_stage(self, user, course, stage):
        """Create/update an enrollment and matching LessonProgress records."""
        required_lessons = list(
            Lesson.objects.filter(module__course=course, is_required=True)
            .order_by('module__order', 'order')
        )
        optional_lessons = list(
            Lesson.objects.filter(module__course=course, is_required=False)
            .order_by('module__order', 'order')
        )
        total = len(required_lessons)

        if stage == 'done':
            lessons_to_complete = required_lessons
            # Fully engaged learners also complete optional content (quizzes etc.)
            optional_to_complete = optional_lessons
        elif stage == 'half':
            lessons_to_complete = required_lessons[:max(1, total // 2)]
            # Complete optional items only in already-visited modules
            visited_modules = {les.module_id for les in lessons_to_complete}
            optional_to_complete = [les for les in optional_lessons if les.module_id in visited_modules]
        elif stage == 'quarter':
            lessons_to_complete = required_lessons[:max(1, total // 4)]
            optional_to_complete = []
        else:  # 'start'
            lessons_to_complete = []
            optional_to_complete = []

        for lesson in lessons_to_complete + optional_to_complete:
            LessonProgress.objects.get_or_create(user=user, lesson=lesson)

        completed = len(lessons_to_complete)
        progress_pct = round(completed / total * 100) if total else 0

        current_module = None
        if lessons_to_complete:
            current_module = lessons_to_complete[-1].module

        Enrollment.objects.update_or_create(
            user=user,
            course=course,
            defaults={
                'progress_pct': progress_pct,
                'current_module': current_module,
            },
        )

    def _seed_teacher_cohort(self, creator):
        cohort_users = []
        for idx, (username, first, last, initials) in enumerate(cohort_data.COHORT):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last},
            )
            if created:
                user.set_password('demo1234')
                user.save()
            subject_slug = COHORT_SUBJECT_SLUGS[idx % len(COHORT_SUBJECT_SLUGS)]
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'user_type': UserProfile.UserType.TEACHER,
                    'avatar_initials': initials,
                    'subject': self.subjects.get(subject_slug),
                },
            )
            cohort_users.append(user)

        total_enrollments = 0
        for course_title, assignments in cohort_data.COHORT_ENROLLMENTS.items():
            course = Course.objects.filter(title=course_title).first()
            if not course:
                self.stdout.write(self.style.WARNING(f'  Course not found: {course_title}'))
                continue
            for teacher_idx, stage in assignments:
                self._enroll_at_stage(cohort_users[teacher_idx], course, stage)
                total_enrollments += 1

        self.stdout.write(
            f'  Cohort: {len(cohort_users)} teachers, {total_enrollments} enrollments seeded'
        )
