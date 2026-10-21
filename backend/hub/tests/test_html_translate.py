import re
from unittest import mock

from django.test import SimpleTestCase

from hub.html_translate import looks_like_html, translate_html


def upper_text(fragment):
    """A well-behaved fake model: uppercases the text between tags only."""
    return re.sub(r'>([^<]+)<', lambda m: '>' + m.group(1).upper() + '<', '>' + fragment + '<')[1:-1]


def upper(text):
    return text.upper()


class TranslateHtmlTests(SimpleTestCase):
    def test_looks_like_html(self):
        self.assertTrue(looks_like_html('<p>Hi</p>'))
        self.assertFalse(looks_like_html('Plain text, 3 < 4'))

    def test_table_and_formatting_keep_their_structure(self):
        html = ('<h2>Risks</h2><p>Some <strong>bold</strong> and a <a href="https://x.eu/a">link</a>.</p>'
                '<table><thead><tr><th>Name</th><th>Level</th></tr></thead>'
                '<tbody><tr><td colspan="2">Bias</td></tr></tbody></table>')
        out = translate_html(html, upper_text, upper)
        self.assertEqual(out, '<h2>RISKS</h2><p>SOME <strong>BOLD</strong> AND A <a href="https://x.eu/a">LINK</a>.</p>'
                              '<table><thead><tr><th>NAME</th><th>LEVEL</th></tr></thead>'
                              '<tbody><tr><td colspan="2">BIAS</td></tr></tbody></table>')

    def test_image_inside_paragraph_survives_and_url_never_sent(self):
        seen = []

        def model(fragment):
            seen.append(fragment)
            return upper_text(fragment)
        html = '<p>Look <img src="https://aidea-hub.eu/media/x.png" alt="a chart" width="300"> here</p>'
        out = translate_html(html, model, upper)
        self.assertNotIn('aidea-hub.eu', ''.join(seen))
        self.assertIn('<img src="https://aidea-hub.eu/media/x.png" alt="A CHART" width="300">', out)
        self.assertTrue(out.startswith('<p>LOOK ') and out.endswith(' HERE</p>'))

    def test_dropped_tag_retries_then_falls_back_to_plain_text(self):
        calls = []

        def drops_tags(fragment):
            calls.append(fragment)
            return re.sub(r'<[^>]+>', '', fragment).upper()
        out = translate_html('<p>Keep <strong>this</strong> bold</p><p>Second</p>', drops_tags, upper)
        self.assertEqual(out, '<p>KEEP THIS BOLD</p><p>SECOND</p>')
        self.assertEqual(len(calls), 3)          # 2 tries for the first block, 1 for the plain second block

    def test_changed_link_is_rejected(self):
        def changes_link(fragment):
            return fragment.replace('https://x.eu/a', 'https://evil.example').upper()
        out = translate_html('<p>See <a href="https://x.eu/a">this</a></p>', changes_link, upper)
        self.assertNotIn('evil', out)
        self.assertEqual(out, '<p>SEE THIS</p>')     # plain-text fallback drops the link markup, never the page

    def test_fallback_keeps_images(self):
        out = translate_html('<p>Hi <b>there</b> <img src="/media/a.png" alt=""></p>',
                             lambda f: 'garbage without tags', upper)
        self.assertIn('<img src="/media/a.png" alt="">', out)
        self.assertTrue(out.startswith('<p>HI THERE'))

    def test_unparseable_answer_falls_back(self):
        out = translate_html('<p>One <em>two</em></p>', lambda f: 'Sure! Here: <<<>>>', upper)
        self.assertEqual(out, '<p>ONE TWO</p>')

    def test_inline_only_content(self):
        self.assertEqual(translate_html('Hello <b>world</b>', upper_text, upper), 'HELLO <b>WORLD</b>')

    def test_empty_blocks_are_not_sent(self):
        model = mock.Mock(side_effect=upper_text)
        translate_html('<p> </p><p>Text</p>', model, upper)
        self.assertEqual(model.call_count, 1)


class TranslateTextRoutingTests(SimpleTestCase):
    @mock.patch('hub.translation._ollama_generate', side_effect=lambda prompt: prompt.rsplit('\n\n', 1)[1].upper())
    def test_html_goes_block_by_block_and_plain_text_as_before(self, generate):
        from hub.translation import translate_text
        self.assertEqual(translate_text('<p>Hi <b>you</b></p><p>Two</p>', 'en', 'el'), '<p>HI <b>YOU</b></p><p>TWO</p>')
        self.assertEqual(generate.call_count, 2)
        self.assertIn('Keep every HTML tag', generate.call_args_list[0].args[0])
        generate.reset_mock()
        self.assertEqual(translate_text('Plain words', 'en', 'el'), 'PLAIN WORDS')
        self.assertNotIn('HTML', generate.call_args.args[0])
