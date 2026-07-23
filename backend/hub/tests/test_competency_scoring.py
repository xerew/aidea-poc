from django.test import SimpleTestCase


class CompetencyLevelTestCase(SimpleTestCase):
    """Competency-band thresholds. The score itself is now the sum of the
    chosen onboarding options' points (exercised end-to-end in test_onboarding)."""

    def _level(self, score):
        from hub.views.onboarding import get_competency_level
        return get_competency_level(score)

    def test_score_0_is_beginner(self):
        self.assertEqual(self._level(0), 'beginner')

    def test_score_2_is_beginner(self):
        self.assertEqual(self._level(2), 'beginner')

    def test_score_3_is_intermediate(self):
        self.assertEqual(self._level(3), 'intermediate')

    def test_score_4_is_intermediate(self):
        self.assertEqual(self._level(4), 'intermediate')

    def test_score_5_is_advanced(self):
        self.assertEqual(self._level(5), 'advanced')

    def test_score_6_is_advanced(self):
        self.assertEqual(self._level(6), 'advanced')
