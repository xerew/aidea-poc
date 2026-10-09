"""Add missing H5P libraries to .h5p files, from the official H5P Hub.

    uv run manage.py h5p_add_libraries ~/Desktop/quiz.h5p [more.h5p …]

Writes <name>-with-libraries.h5p next to each file, checked with the same
rules as an AIDEA upload. Needs internet access to api.h5p.org."""
import io
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand

from hub import h5p, h5p_hub


def ascii_safe(text):
    """Windows consoles (cp1252) cannot print every character."""
    return text.replace('→', '->').replace('—', '-')


class Command(BaseCommand):
    help = 'Add missing H5P libraries to .h5p files from the official H5P Hub (api.h5p.org).'

    def add_arguments(self, parser):
        parser.add_argument('files', nargs='+', help='.h5p files to complete')

    def handle(self, *args, **options):
        for name in options['files']:
            path = Path(name).expanduser()
            data = path.read_bytes()
            result, report = h5p_hub.complete_from_hub(data, lambda lib: h5p_hub.fetch_from_hub(lib))
            if result is data:
                self.stdout.write(f'{path.name}: already includes its libraries - upload it as is.')
                continue
            target = path.with_name(f'{path.stem}-with-libraries.h5p')
            target.write_bytes(result)
            self.stdout.write(f'{path.name}: added {len(report["added"])} libraries -> {target}')
            for line in report['upgraded']:
                self.stdout.write(self.style.WARNING(f'  uses a newer version: {ascii_safe(line)} - test this activity'))
            for line in report['missing']:
                self.stdout.write(self.style.ERROR(f'  not available from the Hub: {line}'))
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    h5p.extract_package(io.BytesIO(result), Path(tmp) / 'check')
                self.stdout.write(self.style.SUCCESS('  passes the AIDEA upload check - ready to upload.'))
            except h5p.H5PError as exc:
                self.stdout.write(self.style.ERROR(f'  still fails the upload check: {ascii_safe(exc.detail)}'))
