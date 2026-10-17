"""Anonymised training data for a future fine-tune (JSON lines)."""
import json

from django.core.management.base import BaseCommand

from hub.ai_review.evidence import anonymise
from hub.models import AIReview


class Command(BaseCommand):
    help = 'Export human-decided AI reviews as anonymised JSON lines (opted-out learners excluded).'

    def add_arguments(self, parser):
        parser.add_argument('--out', default='ai_review_training.jsonl')

    def handle(self, *args, **opts):
        reviews = (AIReview.objects.filter(status='done').exclude(human_verdict='')
                   .exclude(submission__user__profile__ai_training_opt_out=True)
                   .select_related('submission__user', 'submission__resource'))
        count = 0
        with open(opts['out'], 'w', encoding='utf-8') as out:
            for r in reviews:
                sub, user = r.submission, r.submission.user
                out.write(json.dumps({
                    'assignment_id': sub.resource_id,
                    'instructions': sub.resource.instructions if sub.resource_id else '',
                    'rubric': r.rubric,
                    'submission_text': anonymise(sub.text or '', user),
                    'ai': {'verdict': r.verdict, 'confidence': r.confidence, 'criteria': r.criteria_results},
                    'human_verdict': r.human_verdict,
                    'feedback': anonymise(sub.feedback or '', user),
                }, ensure_ascii=False) + '\n')
                count += 1
        self.stdout.write(f'Wrote {count} examples to {opts["out"]}')
