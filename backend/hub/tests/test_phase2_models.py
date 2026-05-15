from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation


class UserProfileNewFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='t1', password='pass')

    def test_preferred_pillars_defaults_to_empty_list(self):
        profile = UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.assertEqual(profile.preferred_pillars, [])

    def test_learning_style_defaults_to_blank(self):
        profile = UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        self.assertEqual(profile.learning_style, '')


class CourseNewFieldsTest(TestCase):
    def setUp(self):
        self.pillar = LearningPillar.objects.create(name='P', slug='p', description='')

    def test_content_format_defaults_to_mixed(self):
        course = Course.objects.create(title='T', pillar=self.pillar)
        self.assertEqual(course.content_format, 'mixed')

    def test_content_format_choices_accepted(self):
        for fmt in ['video', 'text', 'visual', 'interactive', 'mixed']:
            c = Course.objects.create(title=f'C-{fmt}', pillar=self.pillar, content_format=fmt)
            self.assertEqual(c.content_format, fmt)


class CourseRecommendationSourceFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='t2', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        self.course = Course.objects.create(title='T2', pillar=pillar)

    def test_source_defaults_to_personal(self):
        rec = CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.8, reason='test'
        )
        self.assertEqual(rec.source, 'personal')

    def test_source_cf_accepted(self):
        rec = CourseRecommendation.objects.create(
            user=self.user, course=self.course, score=0.6, reason='cf test', source='cf'
        )
        self.assertEqual(rec.source, 'cf')


from hub.models.recommendations import CourseView, RecommendationConfig, RecommendationEvent


class RecommendationConfigTest(TestCase):
    def test_get_creates_singleton_on_first_call(self):
        config = RecommendationConfig.get()
        self.assertEqual(RecommendationConfig.objects.count(), 1)
        self.assertEqual(config.pk, 1)

    def test_get_returns_same_instance_on_second_call(self):
        c1 = RecommendationConfig.get()
        c2 = RecommendationConfig.get()
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(RecommendationConfig.objects.count(), 1)

    def test_default_blend_weights(self):
        config = RecommendationConfig.get()
        self.assertAlmostEqual(config.alpha, 0.3)
        self.assertAlmostEqual(config.beta, 0.5)
        self.assertAlmostEqual(config.gamma, 0.2)

    def test_bandit_inactive_by_default(self):
        config = RecommendationConfig.get()
        self.assertFalse(config.bandit_active)

    def test_save_always_uses_pk_1(self):
        config = RecommendationConfig.get()
        config.alpha = 0.4
        config.save()
        self.assertEqual(RecommendationConfig.objects.count(), 1)
        self.assertAlmostEqual(RecommendationConfig.objects.get(pk=1).alpha, 0.4)


class CourseViewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tv1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P3', slug='p3', description='')
        self.course = Course.objects.create(title='TV', pillar=pillar)

    def test_course_view_created(self):
        cv = CourseView.objects.create(user=self.user, course=self.course)
        self.assertIsNotNone(cv.created_at)
        self.assertEqual(CourseView.objects.filter(user=self.user).count(), 1)

    def test_multiple_views_allowed(self):
        CourseView.objects.create(user=self.user, course=self.course)
        CourseView.objects.create(user=self.user, course=self.course)
        self.assertEqual(CourseView.objects.filter(user=self.user, course=self.course).count(), 2)


class RecommendationEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='re1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P4', slug='p4', description='')
        self.course = Course.objects.create(title='RE', pillar=pillar)

    def test_all_event_types_accepted(self):
        for et in ['shown', 'clicked', 'enrolled', 'completed']:
            ev = RecommendationEvent.objects.create(
                user=self.user,
                course=self.course,
                event_type=et,
                rank=1,
                source='personal',
                weights_snapshot={'alpha': 0.3},
            )
            self.assertEqual(ev.event_type, et)

    def test_cf_source_accepted(self):
        ev = RecommendationEvent.objects.create(
            user=self.user, course=self.course,
            event_type='shown', rank=1, source='cf',
            weights_snapshot={},
        )
        self.assertEqual(ev.source, 'cf')
