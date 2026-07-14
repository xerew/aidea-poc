from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import (
    Course,
    Enrollment,
    LearningPillar,
    Lesson,
    LessonProgress,
    Module,
    UserProfile,
)


class LearnerProgressBase(APITestCase):
    """
    Shared fixtures for CourseLearn / LessonDetail / LessonComplete tests.

    Course structure:
        Module 1 (order=1)
            Lesson 1  – text,  required, order=1, 10 min
            Lesson 2  – video, required, order=2, 15 min
        Module 2 (order=2)
            Lesson 3  – quiz,  required, order=1
            Lesson 4  – text,  optional, order=2
    """

    def setUp(self):
        self.teacher = User.objects.create_user(username="t1", password="testpass123")
        UserProfile.objects.create(user=self.teacher, user_type=UserProfile.UserType.TEACHER)

        self.other = User.objects.create_user(username="t2", password="testpass123")
        UserProfile.objects.create(user=self.other, user_type=UserProfile.UserType.TEACHER)

        self.pillar = LearningPillar.objects.create(
            name="Teach with AI", slug="teach-with-ai", description="", order=1,
        )
        self.course = Course.objects.create(
            title="AI Basics", pillar=self.pillar, is_published=True,
        )
        self.unpublished = Course.objects.create(
            title="Draft", pillar=self.pillar, is_published=False,
        )

        self.mod1 = Module.objects.create(title="Mod 1", course=self.course, order=1)
        self.mod2 = Module.objects.create(title="Mod 2", course=self.course, order=2)

        self.lesson1 = Lesson.objects.create(
            title="L1", module=self.mod1, lesson_type="text",
            is_required=True, order=1, duration_minutes=10,
        )
        self.lesson2 = Lesson.objects.create(
            title="L2", module=self.mod1, lesson_type="video",
            is_required=True, order=2, duration_minutes=15,
        )
        self.lesson3 = Lesson.objects.create(
            title="L3", module=self.mod2, lesson_type="quiz",
            quiz_data=[{
                "question": "What is AI?",
                "options": [
                    {"text": "Artificial Intelligence", "is_correct": True},
                    {"text": "Automated Input", "is_correct": False},
                ],
            }],
            is_required=True, order=1,
        )
        self.lesson4 = Lesson.objects.create(
            title="L4", module=self.mod2, lesson_type="text",
            is_required=False, order=2,
        )

        self.enrollment = Enrollment.objects.create(user=self.teacher, course=self.course)
        self.client.force_authenticate(user=self.teacher)

    def _learn_url(self, course=None):
        return reverse("course-learn", kwargs={"pk": (course or self.course).pk})

    def _lesson_url(self, lesson):
        return reverse("lesson-detail", kwargs={"pk": self.course.pk, "lesson_pk": lesson.pk})

    def _complete_url(self, lesson):
        return reverse("lesson-complete", kwargs={"pk": self.course.pk, "lesson_pk": lesson.pk})


# ── CourseLearnView tests ──────────────────────────────────────────────────────

class CourseLearnViewTestCase(LearnerProgressBase):

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self._learn_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_404_for_unpublished_course(self):
        Enrollment.objects.create(user=self.teacher, course=self.unpublished)
        response = self.client.get(self._learn_url(self.unpublished))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_403_when_not_enrolled(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self._learn_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_course_title_and_progress(self):
        response = self.client.get(self._learn_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "AI Basics")
        self.assertEqual(response.data["progress_pct"], 0)

    def test_returns_all_modules_with_lessons(self):
        response = self.client.get(self._learn_url())
        modules = response.data["modules"]
        self.assertEqual(len(modules), 2)
        lesson_ids = [lsn["id"] for m in modules for lsn in m["lessons"]]
        self.assertIn(self.lesson1.pk, lesson_ids)
        self.assertIn(self.lesson3.pk, lesson_ids)

    def test_lesson_fields_include_type_and_duration(self):
        response = self.client.get(self._learn_url())
        flat = [lsn for m in response.data["modules"] for lsn in m["lessons"]]
        l1 = next(lsn for lsn in flat if lsn["id"] == self.lesson1.pk)
        self.assertEqual(l1["lesson_type"], "text")
        self.assertEqual(l1["duration_minutes"], 10)

    def test_all_lessons_initially_not_completed(self):
        response = self.client.get(self._learn_url())
        flat = [lsn for m in response.data["modules"] for lsn in m["lessons"]]
        self.assertTrue(all(not lsn["is_completed"] for lsn in flat))

    def test_completed_lesson_shows_as_completed(self):
        LessonProgress.objects.create(user=self.teacher, lesson=self.lesson1)
        response = self.client.get(self._learn_url())
        flat = {lsn["id"]: lsn for m in response.data["modules"] for lsn in m["lessons"]}
        self.assertTrue(flat[self.lesson1.pk]["is_completed"])
        self.assertFalse(flat[self.lesson2.pk]["is_completed"])

    def test_first_incomplete_lesson_is_first_lesson_initially(self):
        response = self.client.get(self._learn_url())
        self.assertEqual(response.data["first_incomplete_lesson_id"], self.lesson1.pk)

    def test_first_incomplete_advances_after_completion(self):
        LessonProgress.objects.create(user=self.teacher, lesson=self.lesson1)
        response = self.client.get(self._learn_url())
        self.assertEqual(response.data["first_incomplete_lesson_id"], self.lesson2.pk)

    def test_first_incomplete_is_last_lesson_when_all_done(self):
        for lesson in [self.lesson1, self.lesson2, self.lesson3, self.lesson4]:
            LessonProgress.objects.create(user=self.teacher, lesson=lesson)
        response = self.client.get(self._learn_url())
        self.assertEqual(response.data["first_incomplete_lesson_id"], self.lesson4.pk)

    def test_other_users_completions_not_visible(self):
        Enrollment.objects.create(user=self.other, course=self.course)
        LessonProgress.objects.create(user=self.other, lesson=self.lesson1)
        response = self.client.get(self._learn_url())
        flat = {lsn["id"]: lsn for m in response.data["modules"] for lsn in m["lessons"]}
        self.assertFalse(flat[self.lesson1.pk]["is_completed"])


# ── LessonDetailView tests ─────────────────────────────────────────────────────

class LessonDetailViewTestCase(LearnerProgressBase):

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_404_for_unknown_lesson(self):
        url = reverse("lesson-detail", kwargs={"pk": self.course.pk, "lesson_pk": 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_403_when_not_enrolled(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_all_expected_fields(self):
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in (
            "id", "title", "lesson_type", "content", "quiz_data",
            "duration_minutes", "module_id", "module_title",
            "is_completed", "prev_lesson_id", "next_lesson_id",
        ):
            self.assertIn(field, response.data)

    def test_first_lesson_has_no_prev(self):
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertIsNone(response.data["prev_lesson_id"])
        self.assertEqual(response.data["next_lesson_id"], self.lesson2.pk)

    def test_last_lesson_has_no_next(self):
        response = self.client.get(self._lesson_url(self.lesson4))
        self.assertEqual(response.data["prev_lesson_id"], self.lesson3.pk)
        self.assertIsNone(response.data["next_lesson_id"])

    def test_middle_lesson_has_both_neighbours(self):
        response = self.client.get(self._lesson_url(self.lesson2))
        self.assertEqual(response.data["prev_lesson_id"], self.lesson1.pk)
        self.assertEqual(response.data["next_lesson_id"], self.lesson3.pk)

    def test_cross_module_navigation(self):
        """lesson2 (last in mod1) next should be lesson3 (first in mod2)"""
        response = self.client.get(self._lesson_url(self.lesson2))
        self.assertEqual(response.data["next_lesson_id"], self.lesson3.pk)

    def test_is_completed_false_initially(self):
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertFalse(response.data["is_completed"])

    def test_is_completed_true_after_progress_created(self):
        LessonProgress.objects.create(user=self.teacher, lesson=self.lesson1)
        response = self.client.get(self._lesson_url(self.lesson1))
        self.assertTrue(response.data["is_completed"])

    def test_module_title_matches_parent(self):
        response = self.client.get(self._lesson_url(self.lesson3))
        self.assertEqual(response.data["module_title"], "Mod 2")

    def test_quiz_data_returned_for_quiz_lesson(self):
        response = self.client.get(self._lesson_url(self.lesson3))
        self.assertIsInstance(response.data["quiz_data"], list)
        self.assertEqual(len(response.data["quiz_data"]), 1)
        self.assertIn("question", response.data["quiz_data"][0])


# ── LessonCompleteView tests ───────────────────────────────────────────────────

class LessonCompleteViewTestCase(LearnerProgressBase):

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self._complete_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_404_for_unknown_lesson(self):
        url = reverse("lesson-complete", kwargs={"pk": self.course.pk, "lesson_pk": 9999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_403_when_not_enrolled(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(self._complete_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_marks_lesson_complete_and_returns_payload(self):
        response = self.client.post(self._complete_url(self.lesson1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_completed"])
        self.assertEqual(response.data["lesson_id"], self.lesson1.pk)
        self.assertTrue(
            LessonProgress.objects.filter(user=self.teacher, lesson=self.lesson1).exists()
        )

    def test_is_idempotent(self):
        self.client.post(self._complete_url(self.lesson1))
        self.client.post(self._complete_url(self.lesson1))
        self.assertEqual(
            LessonProgress.objects.filter(user=self.teacher, lesson=self.lesson1).count(), 1,
        )

    def test_progress_pct_one_of_three_required(self):
        """3 required lessons total; completing 1 should give 33%."""
        response = self.client.post(self._complete_url(self.lesson1))
        self.assertEqual(response.data["progress_pct"], 33)

    def test_progress_pct_all_required_lessons(self):
        for lesson in [self.lesson1, self.lesson2, self.lesson3]:
            response = self.client.post(self._complete_url(lesson))
        self.assertEqual(response.data["progress_pct"], 100)

    def test_optional_lesson_excluded_from_denominator(self):
        """lesson4 is optional; completing required lessons still reaches 100%."""
        for lesson in [self.lesson1, self.lesson2, self.lesson3]:
            self.client.post(self._complete_url(lesson))
        response = self.client.post(self._complete_url(self.lesson4))
        self.assertEqual(response.data["progress_pct"], 100)

    def test_enrollment_progress_pct_persisted_to_db(self):
        self.client.post(self._complete_url(self.lesson1))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_pct, 33)

    def test_enrollment_current_module_updated(self):
        self.client.post(self._complete_url(self.lesson3))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.current_module_id, self.mod2.pk)

    def test_other_users_progress_is_independent(self):
        Enrollment.objects.create(user=self.other, course=self.course)
        self.client.post(self._complete_url(self.lesson1))
        self.assertFalse(
            LessonProgress.objects.filter(user=self.other, lesson=self.lesson1).exists()
        )

    def test_course_learn_progress_reflects_completion(self):
        """After completing lesson1, /learn/ should return updated progress_pct."""
        self.client.post(self._complete_url(self.lesson1))
        response = self.client.get(self._learn_url())
        self.assertEqual(response.data["progress_pct"], 33)

    def test_home_continue_learning_includes_course_id(self):
        """ContinueLearningSerializer must expose course_id for the frontend resume link."""
        response = self.client.get(reverse("home"))
        cl = response.data["continue_learning"]
        self.assertIn("course_id", cl)
        self.assertEqual(cl["course_id"], self.course.pk)


# ── CourseDetailView completed_module_ids tests ────────────────────────────────

class CompletedModuleIdsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mod_done", password="pass12345")
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name="P", slug="p", order=1)
        self.course = Course.objects.create(
            title="C", pillar=pillar, level="beginner", duration_hours=1, is_published=True,
        )
        self.m1 = Module.objects.create(course=self.course, title="M1", order=1)
        self.m2 = Module.objects.create(course=self.course, title="M2", order=2)
        self.l1 = Lesson.objects.create(
            module=self.m1, title="L1", lesson_type="text", order=1, is_required=True,
        )
        self.l2 = Lesson.objects.create(
            module=self.m2, title="L2", lesson_type="text", order=1, is_required=True,
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def _detail_url(self):
        return reverse("course-detail", kwargs={"pk": self.course.pk})

    def test_completed_module_ids(self):
        LessonProgress.objects.create(user=self.user, lesson=self.l1)
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["completed_module_ids"], [self.m1.id])
