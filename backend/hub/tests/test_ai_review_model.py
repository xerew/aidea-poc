import json
from unittest import mock

from django.test import SimpleTestCase

from hub.ai_review import model
from hub.ai_review.evidence import Evidence

CRITERIA = [
    {'id': 'c1', 'name': 'Three risks', 'met': 'Names at least three AI risks', 'required': True},
    {'id': 'c2', 'name': 'Sources', 'met': 'Cites a source', 'required': False},
]


def answer(**over):
    data = {
        'criteria': [{'id': 'c1', 'status': 'met', 'reason': 'Lists bias, privacy, errors.'},
                     {'id': 'c2', 'status': 'not_met', 'reason': 'No source.'}],
        'verdict': 'approve', 'confidence': 0.86,
        'learner_feedback': 'Good list.', 'reviewer_notes': '',
    }
    data.update(over)
    return json.dumps(data)


class ParseTests(SimpleTestCase):
    def test_parse_good_answer(self):
        out = model.parse_review(answer(), CRITERIA)
        self.assertEqual((out['verdict'], out['confidence']), ('approve', 0.86))
        self.assertEqual([c['status'] for c in out['criteria']], ['met', 'not_met'])

    def test_parse_rejects_wrong_or_missing_criteria(self):
        with self.assertRaises(model.ReviewModelError):
            model.parse_review(answer(criteria=[{'id': 'c1', 'status': 'met', 'reason': ''}]), CRITERIA)
        with self.assertRaises(model.ReviewModelError):
            model.parse_review(answer(criteria=[{'id': 'zz', 'status': 'met', 'reason': ''},
                                                {'id': 'c2', 'status': 'met', 'reason': ''}]), CRITERIA)

    def test_parse_rejects_bad_values(self):
        for bad in (answer(verdict='maybe'), answer(confidence='high'),
                    answer(criteria=[{'id': 'c1', 'status': 'great', 'reason': ''},
                                     {'id': 'c2', 'status': 'met', 'reason': ''}]),
                    'not json at all', '[]'):
            with self.assertRaises(model.ReviewModelError, msg=bad[:40]):
                model.parse_review(bad, CRITERIA)

    def test_parse_clamps_confidence_and_strips_prose(self):
        out = model.parse_review('Here you go:\n' + answer(confidence=1.7) + '\nThanks', CRITERIA)
        self.assertEqual(out['confidence'], 1.0)


class MessageTests(SimpleTestCase):
    def test_messages_carry_rubric_evidence_checks_language_and_images(self):
        ev = Evidence(text='My answer', documents=[{'name': 'r.pdf', 'text': 'Risk register'}],
                      images=[{'name': 's.png', 'b64': 'AAAA'}], links=['demo (https://youtu.be/x)'])
        msgs = model.build_messages(
            instructions='<p>Describe three AI risks.</p>', criteria=CRITERIA,
            examples=[{'text': 'Bias, privacy, jobs', 'verdict': 'approve', 'reason': 'Three risks'}],
            evidence=ev, checks={'duplicates': [{'learner': 'Bob', 'file': 's.png', 'match': 'identical'}]},
            language='el',
        )
        user = msgs[-1]
        self.assertEqual(user['images'], ['AAAA'])
        for needle in ('Describe three AI risks.', '[c1]', 'Names at least three AI risks', 'My answer',
                       'Risk register', 'cannot be watched', 'Bob', 'Greek', 'Bias, privacy, jobs'):
            self.assertIn(needle, user['content'])
        self.assertNotIn('<p>', user['content'])


class ReviewCallTests(SimpleTestCase):
    def call(self):
        return model.review_submission(instructions='x', criteria=CRITERIA, examples=[], evidence=Evidence(text='a'),
                                       checks={}, language='en', model='m')

    def test_retries_once_after_a_malformed_answer(self):
        with mock.patch.object(model, '_chat', side_effect=['nope', answer()]) as chat:
            self.assertEqual(self.call()['verdict'], 'approve')
        self.assertEqual(chat.call_count, 2)

    def test_two_malformed_answers_raise(self):
        with mock.patch.object(model, '_chat', side_effect=['nope', 'still nope']):
            with self.assertRaises(model.ReviewModelError):
                self.call()

    def test_offline_is_not_retried_here(self):
        with mock.patch.object(model, '_chat', side_effect=model.ModelOffline('down')) as chat:
            with self.assertRaises(model.ModelOffline):
                self.call()
        self.assertEqual(chat.call_count, 1)


class DraftTests(SimpleTestCase):
    def test_draft_rubric_returns_ids_and_flags(self):
        raw = json.dumps({'criteria': [
            {'name': 'Three risks', 'met': 'Names three risks', 'required': True},
            {'name': 'Source', 'met': 'Cites a source', 'required': False},
        ]})
        with mock.patch.object(model, '_chat', return_value=raw):
            crit = model.draft_rubric(title='T', instructions='<p>Describe</p>', language='en', model='m')
        self.assertEqual([(c['id'], c['required']) for c in crit], [('c1', True), ('c2', False)])
