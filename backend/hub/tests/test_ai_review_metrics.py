from types import SimpleNamespace

from django.test import SimpleTestCase

from hub.ai_review.metrics import cohen_kappa, summarise, wilson_lower

A, C = 'approve', 'changes_requested'


class MetricsTests(SimpleTestCase):
    def test_wilson_lower_bound(self):
        self.assertAlmostEqual(wilson_lower(29, 30), 0.833, places=3)   # 97% observed, 83% safe
        self.assertAlmostEqual(wilson_lower(30, 30), 0.886, places=3)
        self.assertAlmostEqual(wilson_lower(35, 35), 0.901, places=3)
        self.assertIsNone(wilson_lower(0, 0))

    def test_kappa_corrects_for_chance(self):
        # An AI that always approves, where humans approve 9 in 10: 90% agreement, no skill.
        self.assertAlmostEqual(cohen_kappa([(A, A)] * 9 + [(A, C)]), 0.0)
        self.assertAlmostEqual(cohen_kappa([(A, A)] * 8 + [(A, C), (C, C)]), 0.615, places=3)
        self.assertIsNone(cohen_kappa([(A, A)] * 5))       # undefined: both only ever approve
        self.assertIsNone(cohen_kappa([]))
        self.assertAlmostEqual(cohen_kappa([('unsure', A), (A, A), (C, C)]), 1.0)   # unsure is ignored

    def test_summarise_feedback_use(self):
        def review(used, similarity):
            return SimpleNamespace(verdict=A, human_verdict=A, agreed=True, criteria_results=[], rubric=[],
                                   feedback_used=used, feedback_similarity=similarity)
        stats = summarise([review(True, 1.0), review(True, 0.6), review(False, None), review(False, None)])
        self.assertEqual((stats['feedback_used'], stats['feedback_unchanged']), (0.5, 0.5))

    def test_summarise_empty(self):
        stats = summarise([])
        self.assertEqual((stats['reviews'], stats['agreement'], stats['kappa'], stats['most_missed']), (0, None, None, None))
