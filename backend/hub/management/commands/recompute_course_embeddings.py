from django.core.management.base import BaseCommand

from hub.models import Course
from hub.tasks import compute_course_embeddings, recompute_all_recommendations


class Command(BaseCommand):
    help = (
        'Recompute the sentence embedding of every published course (run after '
        'changing what goes into hub.personalization.course_embedding_text), then '
        'queue a recommendations refresh for all users.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--no-recommendations', action='store_true',
                            help='Only recompute embeddings.')

    def handle(self, *args, **options):
        ids = list(Course.objects.filter(is_published=True).values_list('id', flat=True))
        for course_id in ids:
            compute_course_embeddings(course_id)  # synchronous: finishes before we return
        self.stdout.write(self.style.SUCCESS(f'Recomputed embeddings for {len(ids)} courses.'))
        if not options['no_recommendations']:
            recompute_all_recommendations.delay()
            self.stdout.write('Queued a recommendations refresh for all users.')
