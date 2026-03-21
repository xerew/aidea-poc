from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Course,
    CourseEditHistory,
    Enrollment,
    LearningPillar,
    Lesson,
    Module,
    UserProfile,
)


class AuthTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            first_name='Nikos',
            last_name='Grammatikos',
        )
        UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            avatar_initials='NG',
        )

    def test_login_returns_tokens_and_user(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'teacher1')
        self.assertEqual(response.data['user']['profile']['user_type'], 'teacher')
        self.assertEqual(response.data['user']['profile']['avatar_initials'], 'NG')

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access_token(self):
        login = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        response = self.client.post(reverse('auth-refresh'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(reverse('auth-login'), {
            'username': 'teacher1',
            'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.post(reverse('auth-logout'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Blacklisted token can no longer be refreshed
        refresh_response = self.client.post(reverse('auth-refresh'), {
            'refresh': login.data['refresh'],
        })
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse('auth-logout'), {'refresh': 'sometoken'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HomeViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            first_name='Nikos',
            last_name='Grammatikos',
        )
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)

        self.pillar1 = LearningPillar.objects.create(
            name='Teach with AI', slug='teach-with-ai',
            description='Learn to use AI tools.', order=1,
        )
        self.pillar2 = LearningPillar.objects.create(
            name='Teach for AI', slug='teach-for-ai',
            description='Prepare students for AI.', order=2,
        )

        self.course1 = Course.objects.create(title='Course 1', pillar=self.pillar1)
        self.course2 = Course.objects.create(title='Course 2', pillar=self.pillar1)
        self.module1 = Module.objects.create(title='Module 1', course=self.course1, order=1)
        self.module2 = Module.objects.create(title='Module 2', course=self.course1, order=2)

        self.client.force_authenticate(user=self.user)

    def test_home_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_home_no_enrollments(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['continue_learning'])
        self.assertEqual(len(response.data['pillars']), 2)

    def test_home_continue_learning(self):
        Enrollment.objects.create(
            user=self.user,
            course=self.course1,
            current_module=self.module2,
            progress_pct=65,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cl = response.data['continue_learning']
        self.assertEqual(cl['course_title'], 'Course 1')
        self.assertEqual(cl['current_module_title'], 'Module 2')
        self.assertEqual(cl['progress_pct'], 65)

    def test_home_pillars_course_count(self):
        response = self.client.get(reverse('home'))
        pillars = {p['slug']: p for p in response.data['pillars']}
        self.assertEqual(pillars['teach-with-ai']['course_count'], 2)
        self.assertEqual(pillars['teach-for-ai']['course_count'], 0)

    def test_home_pillars_progress_no_enrollments(self):
        response = self.client.get(reverse('home'))
        for pillar in response.data['pillars']:
            self.assertEqual(pillar['progress_pct'], 0)

    def test_home_pillars_progress_with_enrollments(self):
        Enrollment.objects.create(user=self.user, course=self.course1, progress_pct=40)
        Enrollment.objects.create(user=self.user, course=self.course2, progress_pct=60)
        response = self.client.get(reverse('home'))
        pillars = {p['slug']: p for p in response.data['pillars']}
        self.assertEqual(pillars['teach-with-ai']['progress_pct'], 50)
        self.assertEqual(pillars['teach-for-ai']['progress_pct'], 0)

    def test_home_continue_learning_is_most_recently_accessed(self):
        Enrollment.objects.create(
            user=self.user, course=self.course1, progress_pct=30,
        )
        enrollment2 = Enrollment.objects.create(
            user=self.user, course=self.course2, progress_pct=80,
        )
        # Touch enrollment2 so it becomes most recently accessed
        enrollment2.save()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.data['continue_learning']['course_title'], 'Course 2')


# ── Authoring helpers ─────────────────────────────────────────────────────────

class AuthoringTestCase(APITestCase):
    """Base class that sets up a content creator, a teacher, and shared course data."""

    def setUp(self):
        self.creator = User.objects.create_user(username='creator1', password='testpass123')
        UserProfile.objects.create(user=self.creator, user_type=UserProfile.UserType.CONTENT_CREATOR)

        self.teacher = User.objects.create_user(username='teacher1', password='testpass123')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

        self.pillar1 = LearningPillar.objects.create(
            name='Teach with AI', slug='teach-with-ai', description='Use AI tools.', order=1,
        )
        self.pillar2 = LearningPillar.objects.create(
            name='Teach for AI', slug='teach-for-ai', description='Prepare students.', order=2,
        )
        self.course = Course.objects.create(
            title='Intro to AI',
            description='A beginner course.',
            pillar=self.pillar1,
            level='beginner',
            duration_hours=4,
            learning_outcomes=['Outcome A', 'Outcome B'],
        )
        self.module1 = Module.objects.create(
            title='Module 1', description='First module.', course=self.course,
            order=1, duration_minutes=30,
        )
        self.module2 = Module.objects.create(
            title='Module 2', description='Second module.', course=self.course,
            order=2, duration_minutes=45,
        )

    def _login_as(self, user):
        self.client.force_authenticate(user=user)


# ── Permission tests ──────────────────────────────────────────────────────────

class AuthoringPermissionTestCase(AuthoringTestCase):

    AUTHORING_URLS = [
        ('authoring-pillars', None),
        ('authoring-courses', None),
    ]

    def _course_detail_url(self):
        return reverse('authoring-course-detail', kwargs={'pk': self.course.pk})

    def _module_create_url(self):
        return reverse('authoring-module-create', kwargs={'pk': self.course.pk})

    def _module_detail_url(self):
        return reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': self.module1.pk})

    def test_unauthenticated_cannot_access_authoring(self):
        for url_name, kwargs in self.AUTHORING_URLS:
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_cannot_access_authoring_courses_list(self):
        self._login_as(self.teacher)
        response = self.client.get(reverse('authoring-courses'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_access_authoring_pillars(self):
        self._login_as(self.teacher)
        response = self.client.get(reverse('authoring-pillars'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_get_course_for_editing(self):
        self._login_as(self.teacher)
        response = self.client.get(self._course_detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_patch_course(self):
        self._login_as(self.teacher)
        response = self.client.patch(self._course_detail_url(), {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_create_module(self):
        self._login_as(self.teacher)
        response = self.client.post(self._module_create_url(), {'title': 'New'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_patch_module(self):
        self._login_as(self.teacher)
        response = self.client.patch(self._module_detail_url(), {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_delete_module(self):
        self._login_as(self.teacher)
        response = self.client.delete(self._module_detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_content_creator_can_access_authoring_courses(self):
        self._login_as(self.creator)
        response = self.client.get(reverse('authoring-courses'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ── Pillars ───────────────────────────────────────────────────────────────────

class AuthoringPillarsTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)

    def test_returns_all_pillars(self):
        response = self.client.get(reverse('authoring-pillars'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_pillar_fields(self):
        response = self.client.get(reverse('authoring-pillars'))
        pillar = response.data[0]
        for field in ('id', 'name', 'slug'):
            self.assertIn(field, pillar)


# ── Published / unpublished visibility ───────────────────────────────────────

class PublishedVisibilityTestCase(APITestCase):
    """Unpublished courses must not be visible to teachers."""

    def setUp(self):
        self.teacher = User.objects.create_user(username='t1', password='testpass123')
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

        self.pillar = LearningPillar.objects.create(
            name='Pillar', slug='pillar', description='', order=1,
        )
        self.published = Course.objects.create(
            title='Published', pillar=self.pillar, is_published=True,
        )
        self.draft = Course.objects.create(
            title='Draft', pillar=self.pillar, is_published=False,
        )
        self.client.force_authenticate(user=self.teacher)

    def test_courses_list_excludes_unpublished(self):
        response = self.client.get(reverse('courses'))
        titles = [c['title'] for c in response.data]
        self.assertIn('Published', titles)
        self.assertNotIn('Draft', titles)

    def test_course_detail_returns_404_for_unpublished(self):
        response = self.client.get(reverse('course-detail', kwargs={'pk': self.draft.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_course_detail_works_for_published(self):
        response = self.client.get(reverse('course-detail', kwargs={'pk': self.published.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enroll_returns_404_for_unpublished(self):
        response = self.client.post(reverse('course-enroll', kwargs={'pk': self.draft.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ── Publish endpoint ──────────────────────────────────────────────────────────

class CoursePublishTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-course-publish', kwargs={'pk': self.course.pk})

    def test_publish_sets_is_published(self):
        self.client.post(self.url)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_published)

    def test_publish_returns_200_with_course_data(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_published'])

    def test_publish_records_history(self):
        self.client.post(self.url)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('course_published', history.changes)

    def test_publish_already_published_returns_400(self):
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publish_nonexistent_course_returns_404(self):
        response = self.client.post(reverse('authoring-course-publish', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_publish(self):
        self._login_as(self.teacher)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Locked editing after publish ──────────────────────────────────────────────

class PublishedCourseLockTestCase(AuthoringTestCase):
    """Once published, courses and their modules cannot be mutated."""

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.course.is_published = True
        self.course.save()

    def test_patch_published_course_returns_400(self):
        url = reverse('authoring-course-detail', kwargs={'pk': self.course.pk})
        response = self.client.patch(url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_published_course_does_not_change_title(self):
        url = reverse('authoring-course-detail', kwargs={'pk': self.course.pk})
        self.client.patch(url, {'title': 'Hacked'})
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Intro to AI')

    def test_add_module_to_published_course_returns_400(self):
        url = reverse('authoring-module-create', kwargs={'pk': self.course.pk})
        response = self.client.post(url, {'title': 'New', 'duration_minutes': 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_module_on_published_course_returns_400(self):
        url = reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': self.module1.pk})
        response = self.client.patch(url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_module_on_published_course_returns_400(self):
        url = reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': self.module1.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_published_course_still_readable_in_authoring(self):
        url = reverse('authoring-course-detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_published'])


# ── Course creation ───────────────────────────────────────────────────────────

class CourseCreateTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-courses')
        self.valid_payload = {
            'title': 'Brand New Course',
            'description': 'A fresh course.',
            'level': 'intermediate',
            'pillar_id': self.pillar1.pk,
            'duration_hours': 6,
            'learning_outcomes': ['Learn X', 'Learn Y'],
        }

    def test_create_course_returns_201(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_course_persists_to_db(self):
        self.client.post(self.url, self.valid_payload, format='json')
        self.assertTrue(Course.objects.filter(title='Brand New Course').exists())

    def test_create_course_response_includes_id_and_pillar(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertIn('id', response.data)
        self.assertEqual(response.data['title'], 'Brand New Course')
        self.assertEqual(response.data['pillar']['id'], self.pillar1.pk)

    def test_create_course_sets_all_fields(self):
        self.client.post(self.url, self.valid_payload, format='json')
        course = Course.objects.get(title='Brand New Course')
        self.assertEqual(course.description, 'A fresh course.')
        self.assertEqual(course.level, 'intermediate')
        self.assertEqual(course.pillar, self.pillar1)
        self.assertEqual(course.duration_hours, 6)
        self.assertEqual(course.learning_outcomes, ['Learn X', 'Learn Y'])

    def test_create_course_records_history(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        course = Course.objects.get(pk=response.data['id'])
        history = CourseEditHistory.objects.get(course=course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('course_created', history.changes)
        self.assertEqual(history.changes['course_created']['title'], 'Brand New Course')

    def test_create_course_missing_title_returns_400(self):
        payload = {**self.valid_payload}
        del payload['title']
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_course_missing_pillar_returns_400(self):
        payload = {**self.valid_payload}
        del payload['pillar_id']
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_course_invalid_level_returns_400(self):
        payload = {**self.valid_payload, 'level': 'expert'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_create_course(self):
        self._login_as(self.teacher)
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_still_works_without_pillar_id(self):
        # Ensure removing required=False from pillar_id didn't break partial PATCH
        detail_url = reverse('authoring-course-detail', kwargs={'pk': self.course.pk})
        response = self.client.patch(detail_url, {'title': 'Patched Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Patched Title')


# ── Authoring courses list ────────────────────────────────────────────────────

class AuthoringCoursesListTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)

    def test_returns_all_courses(self):
        Course.objects.create(title='Course 2', pillar=self.pillar2)
        response = self.client.get(reverse('authoring-courses'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_course_includes_modules(self):
        response = self.client.get(reverse('authoring-courses'))
        course_data = next(c for c in response.data if c['id'] == self.course.pk)
        self.assertEqual(len(course_data['modules']), 2)

    def test_course_includes_pillar(self):
        response = self.client.get(reverse('authoring-courses'))
        course_data = response.data[0]
        self.assertIn('pillar', course_data)
        self.assertIn('slug', course_data['pillar'])


# ── Authoring course detail ───────────────────────────────────────────────────

class AuthoringCourseDetailTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-course-detail', kwargs={'pk': self.course.pk})

    def test_get_returns_course(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Intro to AI')
        self.assertEqual(len(response.data['modules']), 2)

    def test_get_nonexistent_course_returns_404(self):
        response = self.client.get(reverse('authoring-course-detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_title(self):
        response = self.client.patch(self.url, {'title': 'Updated Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Updated Title')

    def test_patch_updates_description(self):
        response = self.client.patch(self.url, {'description': 'New description.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.description, 'New description.')

    def test_patch_updates_level(self):
        response = self.client.patch(self.url, {'level': 'advanced'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.level, 'advanced')

    def test_patch_updates_duration_hours(self):
        response = self.client.patch(self.url, {'duration_hours': 8})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.duration_hours, 8)

    def test_patch_updates_learning_outcomes(self):
        new_outcomes = ['New outcome 1', 'New outcome 2', 'New outcome 3']
        response = self.client.patch(self.url, {'learning_outcomes': new_outcomes}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.learning_outcomes, new_outcomes)

    def test_patch_updates_pillar(self):
        response = self.client.patch(self.url, {'pillar_id': self.pillar2.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.pillar_id, self.pillar2.pk)

    def test_patch_nonexistent_course_returns_404(self):
        response = self.client.patch(
            reverse('authoring-course-detail', kwargs={'pk': 9999}), {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── History recording ──

    def test_patch_creates_history_for_changed_fields(self):
        self.client.patch(self.url, {'title': 'New Title', 'duration_hours': 10})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 1)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('title', history.changes)
        self.assertIn('duration_hours', history.changes)
        self.assertEqual(history.changes['title']['old'], 'Intro to AI')
        self.assertEqual(history.changes['title']['new'], 'New Title')

    def test_patch_records_old_and_new_values(self):
        self.client.patch(self.url, {'duration_hours': 99})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.changes['duration_hours']['old'], 4)
        self.assertEqual(history.changes['duration_hours']['new'], 99)

    def test_patch_records_pillar_change_by_name(self):
        self.client.patch(self.url, {'pillar_id': self.pillar2.pk})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('pillar', history.changes)
        self.assertEqual(history.changes['pillar']['old'], 'Teach with AI')
        self.assertEqual(history.changes['pillar']['new'], 'Teach for AI')

    def test_patch_with_no_actual_changes_creates_no_history(self):
        # Send same values as already stored
        self.client.patch(self.url, {'title': 'Intro to AI', 'duration_hours': 4})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 0)

    def test_multiple_patches_each_create_separate_history_entry(self):
        self.client.patch(self.url, {'title': 'First edit'})
        self.client.patch(self.url, {'title': 'Second edit'})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 2)


# ── Module creation ───────────────────────────────────────────────────────────

class AuthoringModuleCreateTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-module-create', kwargs={'pk': self.course.pk})

    def test_creates_module(self):
        response = self.client.post(self.url, {'title': 'New Module', 'duration_minutes': 60})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Module.objects.filter(title='New Module', course=self.course).exists())

    def test_auto_assigns_next_order(self):
        # Existing modules have order 1 and 2; new module should get order 3
        response = self.client.post(self.url, {'title': 'Third Module', 'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        module = Module.objects.get(pk=response.data['id'])
        self.assertEqual(module.order, 3)

    def test_first_module_gets_order_one(self):
        empty_course = Course.objects.create(title='Empty', pillar=self.pillar1)
        url = reverse('authoring-module-create', kwargs={'pk': empty_course.pk})
        response = self.client.post(url, {'title': 'First', 'duration_minutes': 20})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['order'], 1)

    def test_create_module_creates_history(self):
        self.client.post(self.url, {'title': 'New Module', 'duration_minutes': 60})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_added', history.changes)
        self.assertEqual(history.changes['module_added']['title'], 'New Module')

    def test_create_module_nonexistent_course_returns_404(self):
        response = self.client.post(
            reverse('authoring-module-create', kwargs={'pk': 9999}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_module_missing_title_returns_400(self):
        response = self.client.post(self.url, {'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ── Module edit / delete ──────────────────────────────────────────────────────

class AuthoringModuleDetailTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse(
            'authoring-module-detail',
            kwargs={'pk': self.course.pk, 'module_pk': self.module1.pk},
        )

    def test_patch_updates_title(self):
        response = self.client.patch(self.url, {'title': 'Updated Module'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.title, 'Updated Module')

    def test_patch_updates_description(self):
        response = self.client.patch(self.url, {'description': 'New desc.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.description, 'New desc.')

    def test_patch_updates_duration_minutes(self):
        response = self.client.patch(self.url, {'duration_minutes': 90})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.module1.refresh_from_db()
        self.assertEqual(self.module1.duration_minutes, 90)

    def test_patch_creates_history(self):
        self.client.patch(self.url, {'title': 'Renamed Module'})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_edited', history.changes)
        self.assertIn('title', history.changes['module_edited']['fields'])

    def test_patch_history_records_old_and_new(self):
        self.client.patch(self.url, {'duration_minutes': 90})
        history = CourseEditHistory.objects.get(course=self.course)
        field_change = history.changes['module_edited']['fields']['duration_minutes']
        self.assertEqual(field_change['old'], 30)
        self.assertEqual(field_change['new'], 90)

    def test_patch_with_no_changes_creates_no_history(self):
        self.client.patch(self.url, {'title': 'Module 1', 'duration_minutes': 30})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 0)

    def test_patch_nonexistent_module_returns_404(self):
        response = self.client.patch(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_module_belonging_to_other_course_returns_404(self):
        other_course = Course.objects.create(title='Other', pillar=self.pillar1)
        other_module = Module.objects.create(title='Other mod', course=other_course, order=1)
        # Use course pk but module from other course — should 404
        response = self.client.patch(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': other_module.pk}),
            {'title': 'X'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_module(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Module.objects.filter(pk=self.module1.pk).exists())

    def test_delete_creates_history(self):
        self.client.delete(self.url)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertEqual(history.editor, self.creator)
        self.assertIn('module_deleted', history.changes)
        self.assertEqual(history.changes['module_deleted']['title'], 'Module 1')

    def test_delete_nonexistent_module_returns_404(self):
        response = self.client.delete(
            reverse('authoring-module-detail', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ── Module editor (GET with lessons) ──────────────────────────────────────────

class AuthoringModuleEditorTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.lesson1 = Lesson.objects.create(
            module=self.module1, title='Intro Video', lesson_type='video',
            description='Watch this.', order=1, is_required=True,
        )
        self.lesson2 = Lesson.objects.create(
            module=self.module1, title='Key Concepts', lesson_type='text',
            content='Some markdown.', order=2, is_required=False,
        )
        self.url = reverse('authoring-module-editor', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })

    def test_get_returns_module_with_lessons(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Module 1')
        self.assertEqual(len(response.data['lessons']), 2)

    def test_lessons_include_expected_fields(self):
        response = self.client.get(self.url)
        lesson = response.data['lessons'][0]
        for field in ('id', 'title', 'description', 'lesson_type', 'content', 'duration_minutes', 'order', 'is_required'):
            self.assertIn(field, lesson)

    def test_lessons_ordered_by_order(self):
        response = self.client.get(self.url)
        orders = [lesson['order'] for lesson in response.data['lessons']]
        self.assertEqual(orders, sorted(orders))

    def test_get_nonexistent_module_returns_404(self):
        response = self.client.get(
            reverse('authoring-module-editor', kwargs={'pk': self.course.pk, 'module_pk': 9999}),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_access_module_editor(self):
        self._login_as(self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Lesson creation ───────────────────────────────────────────────────────────

class AuthoringLessonCreateTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.url = reverse('authoring-lesson-create', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
        })
        self.valid_payload = {'title': 'New Lesson', 'lesson_type': 'text'}

    def test_create_lesson_returns_201(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_persists_to_db(self):
        self.client.post(self.url, self.valid_payload)
        self.assertTrue(Lesson.objects.filter(title='New Lesson', module=self.module1).exists())

    def test_create_lesson_auto_assigns_order(self):
        Lesson.objects.create(module=self.module1, title='First', lesson_type='text', order=1)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(lesson.order, 2)

    def test_first_lesson_gets_order_one(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.data['order'], 1)

    def test_create_lesson_records_history(self):
        self.client.post(self.url, self.valid_payload)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_added', history.changes)
        self.assertEqual(history.changes['lesson_added']['lesson_title'], 'New Lesson')

    def test_create_lesson_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lesson_nonexistent_module_returns_404(self):
        url = reverse('authoring-lesson-create', kwargs={'pk': self.course.pk, 'module_pk': 9999})
        response = self.client.post(url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_lesson_missing_title_returns_400(self):
        response = self.client.post(self.url, {'lesson_type': 'text'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lesson_invalid_type_returns_400(self):
        response = self.client.post(self.url, {'title': 'X', 'lesson_type': 'podcast'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_cannot_create_lesson(self):
        self._login_as(self.teacher)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_lesson_with_all_fields(self):
        payload = {
            'title': 'Full Lesson',
            'lesson_type': 'video',
            'description': 'A video lesson.',
            'content': '',
            'duration_minutes': 15,
            'is_required': False,
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(lesson.duration_minutes, 15)
        self.assertFalse(lesson.is_required)


# ── Lesson edit / delete ──────────────────────────────────────────────────────

class AuthoringLessonDetailTestCase(AuthoringTestCase):

    def setUp(self):
        super().setUp()
        self._login_as(self.creator)
        self.lesson = Lesson.objects.create(
            module=self.module1, title='Intro Text', lesson_type='text',
            description='Original desc.', content='Original content.',
            duration_minutes=10, order=1, is_required=True,
        )
        self.url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': self.lesson.pk,
        })

    def test_patch_updates_title(self):
        response = self.client.patch(self.url, {'title': 'Updated Title'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Title')

    def test_patch_updates_content(self):
        response = self.client.patch(self.url, {'content': '# New Markdown'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.content, '# New Markdown')

    def test_patch_updates_lesson_type(self):
        response = self.client.patch(self.url, {'lesson_type': 'quiz'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.lesson_type, 'quiz')

    def test_patch_updates_duration(self):
        response = self.client.patch(self.url, {'duration_minutes': 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.duration_minutes, 30)

    def test_patch_updates_is_required(self):
        response = self.client.patch(self.url, {'is_required': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertFalse(self.lesson.is_required)

    def test_patch_creates_history(self):
        self.client.patch(self.url, {'title': 'Renamed Lesson'})
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_edited', history.changes)
        self.assertIn('title', history.changes['lesson_edited']['fields'])

    def test_patch_history_records_old_and_new(self):
        self.client.patch(self.url, {'duration_minutes': 45})
        history = CourseEditHistory.objects.get(course=self.course)
        field_change = history.changes['lesson_edited']['fields']['duration_minutes']
        self.assertEqual(field_change['old'], 10)
        self.assertEqual(field_change['new'], 45)

    def test_patch_with_no_changes_creates_no_history(self):
        self.client.patch(self.url, {'title': 'Intro Text', 'duration_minutes': 10})
        self.assertEqual(CourseEditHistory.objects.filter(course=self.course).count(), 0)

    def test_patch_nonexistent_lesson_returns_404(self):
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': 9999,
        })
        response = self.client.patch(url, {'title': 'X'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_lesson_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.patch(self.url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_lesson_belonging_to_other_module_returns_404(self):
        other_lesson = Lesson.objects.create(
            module=self.module2, title='Other', lesson_type='text', order=1,
        )
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': other_lesson.pk,
        })
        response = self.client.patch(url, {'title': 'X'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_lesson(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_delete_creates_history(self):
        self.client.delete(self.url)
        history = CourseEditHistory.objects.get(course=self.course)
        self.assertIn('lesson_deleted', history.changes)
        self.assertEqual(history.changes['lesson_deleted']['lesson_title'], 'Intro Text')

    def test_delete_on_published_course_returns_400(self):
        self.course.is_published = True
        self.course.save()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_nonexistent_lesson_returns_404(self):
        url = reverse('authoring-lesson-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': 9999,
        })
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_cannot_patch_lesson(self):
        self._login_as(self.teacher)
        response = self.client.patch(self.url, {'title': 'Hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_delete_lesson(self):
        self._login_as(self.teacher)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
