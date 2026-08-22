from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import (
    Course,
    LearningPath,
    LearningPathCourse,
    LearningPillar,
    StudyAssessmentOption,
    StudyAssessmentQuestion,
    StudyConfig,
    StudyParticipant,
    UserLearningPath,
    UserProfile,
)


def make_teacher(username):
    u = User.objects.create_user(username=username, password='pass12345', first_name=username, last_name='T')
    UserProfile.objects.create(user=u, user_type=UserProfile.UserType.TEACHER, competency_score=2)
    return u


def make_admin(username='admin1'):
    u = User.objects.create_user(username=username, password='pass12345')
    UserProfile.objects.create(user=u, user_type=UserProfile.UserType.ADMIN)
    return u


def build_assessment(n=3):
    for i in range(n):
        q = StudyAssessmentQuestion.objects.create(text=f'Q{i}', order=i)
        StudyAssessmentOption.objects.create(question=q, text='right', is_correct=True, order=0)
        StudyAssessmentOption.objects.create(question=q, text='wrong', is_correct=False, order=1)


class StudyTests(APITestCase):
    def setUp(self):
        self.config = StudyConfig.get()
        self.config.enabled = True
        self.config.save()
        self.teacher = make_teacher('steach')
        self.admin = make_admin()

    def _consent(self, user, consent=True):
        self.client.force_authenticate(user)
        return self.client.post('/api/study/consent/', {'consent': consent}, format='json')

    def test_status_flags_consent_needed(self):
        self.client.force_authenticate(self.teacher)
        data = self.client.get('/api/study/status/').data
        self.assertTrue(data['enabled'])
        self.assertTrue(data['needs_consent'])
        self.assertFalse(data['in_study'])

    def test_consent_creates_participant_with_group(self):
        res = self._consent(self.teacher)
        self.assertEqual(res.status_code, 201)
        p = StudyParticipant.objects.get(user=self.teacher)
        self.assertTrue(p.in_study)
        self.assertIn(p.group, ['adaptive', 'fixed'])

    def test_decline_records_exclusion(self):
        self._consent(self.teacher, consent=False)
        p = StudyParticipant.objects.get(user=self.teacher)
        self.assertFalse(p.in_study)

    def test_balanced_allocation(self):
        for i in range(6):
            self._consent(make_teacher(f'bal{i}'))
        adaptive = StudyParticipant.objects.filter(in_study=True, group='adaptive').count()
        fixed = StudyParticipant.objects.filter(in_study=True, group='fixed').count()
        self.assertEqual(adaptive, fixed)  # 3 / 3

    def test_pre_test_scores_and_stores(self):
        build_assessment(3)
        self._consent(self.teacher)
        self.client.force_authenticate(self.teacher)
        questions = self.client.get('/api/study/assessment/').data
        self.assertEqual(questions['phase'], 'pre')
        # Answer every question with its correct option.
        answers = {}
        for q in StudyAssessmentQuestion.objects.all():
            correct = q.options.get(is_correct=True)
            answers[str(q.id)] = correct.id
        res = self.client.post('/api/study/assessment/', {'phase': 'pre', 'answers': answers}, format='json')
        self.assertEqual(res.data['score'], 3)
        self.assertEqual(StudyParticipant.objects.get(user=self.teacher).pre_score, 3)

    def test_post_test_gated_until_open(self):
        build_assessment(2)
        self._consent(self.teacher)
        p = StudyParticipant.objects.get(user=self.teacher)
        p.pre_score = 1
        p.save()
        self.client.force_authenticate(self.teacher)
        # Post not open yet.
        res = self.client.post('/api/study/assessment/', {'phase': 'post', 'answers': {}}, format='json')
        self.assertEqual(res.status_code, 400)
        # Researcher opens it.
        self.config.post_test_open = True
        self.config.save()
        res = self.client.post('/api/study/assessment/', {'phase': 'post', 'answers': {}}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['score'], 0)

    def test_cannot_consent_twice(self):
        self._consent(self.teacher)
        res = self._consent(self.teacher)
        self.assertEqual(res.status_code, 400)

    def test_admin_config_and_summary(self):
        self._consent(self.teacher)
        self.client.force_authenticate(self.admin)
        data = self.client.get('/api/admin/study/').data
        self.assertTrue(data['enabled'])
        self.assertEqual(data['counts']['total'], 1)

    def test_admin_patch_toggles_post_test(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch('/api/admin/study/', {'post_test_open': True}, format='json')
        self.assertTrue(res.data['post_test_open'])
        self.assertTrue(StudyConfig.get().post_test_open)

    def test_non_admin_cannot_access_admin_study(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get('/api/admin/study/').status_code, 403)

    def test_export_returns_xlsx(self):
        self._consent(self.teacher)
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/admin/study/export/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheetml', res['Content-Type'])


class StudyExperienceBranchTests(APITestCase):
    def setUp(self):
        self.config = StudyConfig.get()
        self.config.enabled = True

        self.pillar = LearningPillar.objects.create(name='P', slug='p-study', order=1)
        self.c1 = Course.objects.create(title='C1', pillar=self.pillar, is_published=True)
        self.c2 = Course.objects.create(title='C2', pillar=self.pillar, is_published=True)
        self.control = LearningPath.objects.create(name='Control', slug='control')
        LearningPathCourse.objects.create(path=self.control, course=self.c1, order=0)
        LearningPathCourse.objects.create(path=self.control, course=self.c2, order=1)
        self.config.control_path = self.control
        self.config.save()

        self.teacher = make_teacher('branch_t')
        # Adaptive personalised pathway differs from the control curriculum.
        band = LearningPath.objects.create(name='Band', slug='band')
        UserLearningPath.objects.create(user=self.teacher, path=band, course_ids=[self.c2.id])

    def test_fixed_group_gets_control_curriculum(self):
        StudyParticipant.objects.create(user=self.teacher, in_study=True, group='fixed')
        self.client.force_authenticate(self.teacher)
        data = self.client.get('/api/pathway/').data
        ids = [c['id'] for c in data['courses']]
        self.assertEqual(ids, [self.c1.id, self.c2.id])  # control order

    def test_adaptive_group_keeps_personal_pathway(self):
        StudyParticipant.objects.create(user=self.teacher, in_study=True, group='adaptive')
        self.client.force_authenticate(self.teacher)
        data = self.client.get('/api/pathway/').data
        ids = [c['id'] for c in data['courses']]
        self.assertEqual(ids, [self.c2.id])  # personalised

    def test_fixed_group_gets_no_recommendations(self):
        StudyParticipant.objects.create(user=self.teacher, in_study=True, group='fixed')
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/recommendations/')
        self.assertEqual(res.data, [])


class StudyStatsTests(APITestCase):
    """CONSORT counts, per-group descriptives, gain t-test/Cohen's d and ANCOVA
    over a hand-built participant fixture."""

    def _p(self, username, group, pre, post, in_study=True):
        u = make_teacher(username)
        return StudyParticipant.objects.create(
            user=u, in_study=in_study, group=group if in_study else '',
            pre_score=pre, post_score=post,
        )

    def setUp(self):
        self.config = StudyConfig.get()
        self.config.enabled = True
        self.config.save()
        self.admin = make_admin()
        # Adaptive: bigger gains than fixed.
        self._p('a1', 'adaptive', 2, 8)
        self._p('a2', 'adaptive', 3, 8)
        self._p('a3', 'adaptive', 4, 9)
        self._p('f1', 'fixed', 2, 5)
        self._p('f2', 'fixed', 3, 5)
        self._p('f3', 'fixed', 4, 6)
        # Attrition: consented + did pre but no post.
        self._p('a4', 'adaptive', 5, None)
        # Declined.
        self._p('d1', 'fixed', None, None, in_study=False)

    def _stats(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/admin/study/stats/')
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_consort_counts(self):
        c = self._stats()['consort']
        self.assertEqual(c['enrolled'], 8)
        self.assertEqual(c['consented'], 7)
        self.assertEqual(c['declined'], 1)
        self.assertEqual(c['adaptive']['allocated'], 4)
        self.assertEqual(c['adaptive']['pre_done'], 4)
        self.assertEqual(c['adaptive']['post_done'], 3)
        self.assertEqual(c['adaptive']['analyzed'], 3)
        self.assertEqual(c['adaptive']['attrition'], 1)
        self.assertEqual(c['fixed']['allocated'], 3)
        self.assertEqual(c['fixed']['analyzed'], 3)
        self.assertEqual(c['fixed']['attrition'], 0)

    def test_group_descriptives(self):
        groups = self._stats()['groups']
        a = groups['adaptive']
        self.assertEqual(a['n'], 3)               # only completers
        self.assertEqual(a['pre_mean'], 3.0)
        self.assertAlmostEqual(a['post_mean'], 8.33, places=2)
        self.assertAlmostEqual(a['gain_mean'], 5.33, places=2)
        f = groups['fixed']
        self.assertEqual(f['n'], 3)
        self.assertAlmostEqual(f['gain_mean'], 2.33, places=2)

    def test_gain_test_and_cohens_d(self):
        gt = self._stats()['gain_test']
        self.assertAlmostEqual(gt['mean_diff'], 3.0, places=2)  # 5.33 - 2.33
        self.assertIsNotNone(gt['cohens_d'])
        self.assertGreater(gt['cohens_d'], 0)     # adaptive gained more
        self.assertIn('p', gt)
        self.assertIn('t', gt)

    def test_ancova_keys_and_direction(self):
        an = self._stats()['ancova']
        for key in ('adjusted_diff', 'se', 't', 'df', 'p',
                    'adjusted_mean_adaptive', 'adjusted_mean_fixed'):
            self.assertIn(key, an)
        self.assertGreater(an['adjusted_diff'], 0)  # adaptive higher, adjusting for pre
        self.assertEqual(an['df'], 6 - 3)           # n(6) - params(3)

    def test_stats_admin_only(self):
        teacher = make_teacher('nope')
        self.client.force_authenticate(teacher)
        self.assertEqual(self.client.get('/api/admin/study/stats/').status_code, 403)


class StudyPreregistrationTests(APITestCase):
    def setUp(self):
        self.config = StudyConfig.get()
        self.config.enabled = True
        self.config.save()
        self.admin = make_admin()
        self.teacher = make_teacher('preg_t')

    def test_starts_unlocked(self):
        self.client.force_authenticate(self.admin)
        data = self.client.get('/api/admin/study/preregister/').data
        self.assertIsNone(data['locked_at'])
        self.assertFalse(data['changed_since_lock'])

    def test_patch_saves_hypothesis_without_locking(self):
        self.client.force_authenticate(self.admin)
        data = self.client.patch(
            '/api/admin/study/preregister/', {'hypothesis': 'Adaptive > fixed'}, format='json',
        ).data
        self.assertEqual(data['hypothesis'], 'Adaptive > fixed')
        self.assertIsNone(data['locked_at'])

    def test_lock_snapshots_design(self):
        build_assessment(2)
        self.client.force_authenticate(self.admin)
        data = self.client.post(
            '/api/admin/study/preregister/', {'hypothesis': 'H1'}, format='json',
        ).data
        self.assertIsNotNone(data['locked_at'])
        self.assertEqual(data['hypothesis'], 'H1')
        self.assertFalse(data['changed_since_lock'])

    def test_change_detected_after_lock(self):
        build_assessment(2)
        self.client.force_authenticate(self.admin)
        self.client.post('/api/admin/study/preregister/', {'hypothesis': 'H1'}, format='json')
        # Alter the design after locking.
        build_assessment(1)
        data = self.client.get('/api/admin/study/preregister/').data
        self.assertTrue(data['changed_since_lock'])

    def test_prereg_admin_only(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get('/api/admin/study/preregister/').status_code, 403)
        self.assertEqual(
            self.client.post('/api/admin/study/preregister/', {}, format='json').status_code, 403,
        )
