from django.test import SimpleTestCase


class CompetencyScoringTestCase(SimpleTestCase):
    def _score(self, answers):
        from hub.views.onboarding import score_answers
        return score_answers(answers)

    def _level(self, score):
        from hub.views.onboarding import get_competency_level
        return get_competency_level(score)

    def test_all_correct_gives_6(self):
        self.assertEqual(self._score({'q3': 'b', 'q4': 'b', 'q5': 'b'}), 6)

    def test_all_wrong_gives_0(self):
        self.assertEqual(self._score({'q3': 'a', 'q4': 'a', 'q5': 'a'}), 0)

    def test_partial_correct_q3(self):
        self.assertEqual(self._score({'q3': 'c', 'q4': 'a', 'q5': 'a'}), 1)

    def test_partial_correct_q5(self):
        self.assertEqual(self._score({'q3': 'a', 'q4': 'a', 'q5': 'c'}), 1)

    def test_mixed_gives_correct_total(self):
        # q3=b(2) + q4=c(1) + q5=b(2) = 5
        self.assertEqual(self._score({'q3': 'b', 'q4': 'c', 'q5': 'b'}), 5)

    def test_missing_question_scores_zero(self):
        self.assertEqual(self._score({'q3': 'b'}), 2)

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
