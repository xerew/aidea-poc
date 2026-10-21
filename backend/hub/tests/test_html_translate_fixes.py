"""Regression tests for the final-review findings on structure-safe translation."""
from unittest import mock

from django.test import SimpleTestCase

from hub.html_translate import looks_like_html, translate_html

from .test_html_translate import upper, upper_text


class PlainTextWithAngleBracketsTests(SimpleTestCase):
    def test_prompt_placeholders_are_not_html(self):
        for text in ('Act as a <role> and answer', 'Compare <GPT-4> and <Claude>', 'prompt: <your question here>'):
            self.assertFalse(looks_like_html(text), text)
        for text in ('<p>Hi</p>', 'a <strong>b</strong>', '<table><tr><td>x</td></tr></table>', 'x<br>y'):
            self.assertTrue(looks_like_html(text), text)

    @mock.patch('hub.translation._ollama_generate', side_effect=lambda prompt: prompt.rsplit('\n\n', 1)[1])
    def test_placeholder_text_is_translated_as_plain_text(self, generate):
        from hub.translation import translate_text
        self.assertEqual(translate_text('Act as a <role> and answer', 'en', 'el'), 'Act as a <role> and answer')
        self.assertEqual(generate.call_count, 1)


class ModelChatterTests(SimpleTestCase):
    def test_preamble_before_the_html_is_rejected(self):
        out = translate_html('<p>Look <b>bold</b> here</p>',
                             lambda f: 'Here is the translation:\n' + upper_text(f), upper)
        self.assertEqual(out, '<p>LOOK BOLD HERE</p>')        # fell back to plain text, no preamble stored

    def test_code_fence_is_stripped(self):
        out = translate_html('<p>Look <b>bold</b></p>', lambda f: '```html\n' + upper_text(f) + '\n```', upper)
        self.assertEqual(out, '<p>LOOK <b>BOLD</b></p>')

    def test_answer_far_longer_than_the_source_is_rejected(self):
        out = translate_html('<p>Short <b>text</b></p>',
                             lambda f: upper_text(f).replace('SHORT', 'SHORT ' + 'blah ' * 30), upper)
        self.assertEqual(out, '<p>SHORT TEXT</p>')


class NestedListTests(SimpleTestCase):
    def test_parent_item_text_is_translated(self):
        out = translate_html('<ul><li>Parent <strong>text</strong><ul><li>Child</li></ul></li></ul>', upper_text, upper)
        self.assertEqual(out, '<ul><li>PARENT <strong>TEXT</strong><ul><li>CHILD</li></ul></li></ul>')

    def test_text_around_an_inner_paragraph(self):
        out = translate_html('<li>Top<p>inner</p></li>', upper_text, upper)
        self.assertEqual(out, '<li>TOP<p>INNER</p></li>')


class ControlCharacterTests(SimpleTestCase):
    def test_control_characters_in_model_output_never_crash(self):
        out = translate_html('<p>One <b>two</b></p><p>x <img src="/media/a.png" alt="pic"></p>',
                             lambda f: 'garbage\x1b', lambda t: '\x1bT\x07' + t.upper())
        self.assertIn('TONE TWO', out)
        self.assertIn('alt="TPIC"', out)
