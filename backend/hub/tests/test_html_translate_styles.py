"""Rich-text formatting survives translation where it can (spec 2026-11-03)."""
import re

from django.test import SimpleTestCase

from hub.html_translate import translate_html


class StyledTranslationTests(SimpleTestCase):
    def test_block_and_cell_styles_survive(self):
        html = ('<p style="text-align: center; line-height: 1.5">Hello <b>world</b></p>'
                '<table class="rt-striped"><colgroup><col style="width: 30%"></colgroup>'
                '<tbody><tr><td style="background-color: #f1f5f9">Cell</td></tr></tbody></table>')
        out = translate_html(html, lambda f: f.replace('Hello', 'Γεια').replace('Cell', 'Κελί'), lambda t: t)
        for piece in ['style="text-align: center; line-height: 1.5"', 'Γεια', '<b>world</b>', 'class="rt-striped"',
                      '<col style="width: 30%">', 'style="background-color: #f1f5f9"', 'Κελί']:
            self.assertIn(piece, out)

    def test_styled_span_kept_when_the_model_keeps_it(self):
        html = '<p>Say <span style="color: #b91c1c">hi</span></p>'
        out = translate_html(html, lambda f: f.replace('Say', 'Πες'), lambda t: t)
        self.assertIn('<span style="color: #b91c1c">hi</span>', out)

    def test_styled_span_dropped_by_model_keeps_text_bold_and_block_style(self):
        html = ('<p style="text-align: right"><b>Say</b> <span style="color: #b91c1c">hi</span> '
                '<a href="https://x.org">x</a></p>')

        def model(fragment):  # never returns spans
            return re.sub(r'</?span[^>]*>', '', fragment).replace('Say', 'Πες')
        out = translate_html(html, model, lambda t: 'PLAIN')
        self.assertIn('style="text-align: right"', out)
        self.assertIn('<b>Πες</b>', out)
        self.assertIn('href="https://x.org"', out)
        self.assertNotIn('PLAIN', out)
        self.assertNotIn('<span', out)
