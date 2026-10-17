"""Compare candidate models on submissions humans already decided.

    uv run manage.py ai_review_benchmark --models qwen2.5vl:32b,gemma3:27b --limit 30
"""
import time

from django.core.management.base import BaseCommand
from openpyxl import Workbook

from hub.ai_review import model
from hub.ai_review.evidence import gather
from hub.models import AssignmentSubmission

HUMAN = {'approved': 'approve', 'changes_requested': 'changes_requested'}


class Command(BaseCommand):
    help = 'Benchmark AI review models against human decisions (nothing is stored).'

    def add_arguments(self, parser):
        parser.add_argument('--models', required=True, help='comma-separated Ollama model names')
        parser.add_argument('--limit', type=int, default=30)
        parser.add_argument('--out', default='ai_review_benchmark.xlsx')

    def handle(self, *args, **opts):
        subs = list(
            AssignmentSubmission.objects.filter(status__in=HUMAN, resource__ai_review_config__isnull=False)
            .exclude(resource__ai_review_config__criteria=[])
            .select_related('user__profile', 'resource__ai_review_config').order_by('-submitted_at')[:opts['limit']]
        )
        wb = Workbook()
        summary = wb.active
        summary.title = 'Summary'
        summary.append(['Model', 'Submissions', 'Agreement', 'Approve agreement', 'Avg seconds', 'Failures'])
        answers = wb.create_sheet('Answers')
        answers.append(['Model', 'Submission ID', 'Human', 'AI verdict', 'Confidence', 'Seconds', 'Error', 'Feedback'])
        for name in [m.strip() for m in opts['models'].split(',') if m.strip()]:
            agree = approve_total = approve_ok = failures = 0
            seconds = []
            for sub in subs:
                config = sub.resource.ai_review_config
                started = time.monotonic()
                try:
                    result = model.review_submission(
                        instructions=sub.resource.instructions, criteria=config.criteria,
                        examples=[{'text': e.text, 'verdict': e.verdict, 'reason': e.reason}
                                  for e in sub.resource.ai_review_examples.exclude(source_submission=sub)[:5]],
                        evidence=gather(sub), checks={}, language=getattr(sub.user.profile, 'language', 'en'), model=name)
                    error = ''
                except model.ReviewModelError as exc:
                    result, error = None, str(exc)
                    failures += 1
                took = round(time.monotonic() - started, 1)
                seconds.append(took)
                human = HUMAN[sub.status]
                if result:
                    agree += result['verdict'] == human
                    if result['verdict'] == 'approve':
                        approve_total += 1
                        approve_ok += human == 'approve'
                answers.append([name, sub.id, human, result and result['verdict'], result and result['confidence'],
                                took, error, result and result['learner_feedback']])
            n = len(subs) or 1
            row = [name, len(subs), round(agree / n, 3), round(approve_ok / approve_total, 3) if approve_total else None,
                   round(sum(seconds) / n, 1), failures]
            summary.append(row)
            self.stdout.write(f'{name}: agreement {row[2]}, approve agreement {row[3]}, avg {row[4]} s, failures {failures}')
        wb.save(opts['out'])
        self.stdout.write(f'Wrote {opts["out"]}')
