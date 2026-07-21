from unittest.mock import patch

from django.test import TestCase

from hub.translation import TranslationError, translate_text


class TranslateTextTests(TestCase):
    def test_blank_input_returned_unchanged(self):
        self.assertEqual(translate_text('   ', 'en', 'el'), '   ')
        self.assertEqual(translate_text('', 'en', 'el'), '')

    def test_same_language_is_noop(self):
        self.assertEqual(translate_text('Hello', 'en', 'en'), 'Hello')

    @patch('hub.translation._ollama_generate')
    def test_calls_ollama_and_returns_translation(self, mock_gen):
        mock_gen.return_value = 'Γεια σου'
        out = translate_text('Hello', 'en', 'el')
        self.assertEqual(out, 'Γεια σου')
        prompt = mock_gen.call_args[0][0]
        self.assertIn('English', prompt)
        self.assertIn('Greek', prompt)
        self.assertIn('Hello', prompt)

    @patch('hub.translation._ollama_generate', side_effect=TranslationError('boom'))
    def test_error_propagates(self, _mock):
        with self.assertRaises(TranslationError):
            translate_text('Hello', 'en', 'el')
