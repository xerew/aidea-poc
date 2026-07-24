from django.db import migrations

MEDIA_TYPES = {'image', 'video', 'pdf'}


def forward(apps, schema_editor):
    """Move each existing image/video/pdf lesson's single content URL into the
    new media_items list, so those lessons render through the unified path."""
    Lesson = apps.get_model('hub', 'Lesson')
    for lesson in Lesson.objects.filter(lesson_type__in=MEDIA_TYPES):
        url = (lesson.content or '').strip()
        if url and not lesson.media_items:
            lesson.media_items = [{'type': lesson.lesson_type, 'url': url, 'caption': ''}]
            lesson.content = ''
            lesson.save(update_fields=['media_items', 'content'])


def backward(apps, schema_editor):
    """Best-effort reverse: put the first media item's url back into content."""
    Lesson = apps.get_model('hub', 'Lesson')
    for lesson in Lesson.objects.filter(lesson_type__in=MEDIA_TYPES):
        if lesson.media_items and not lesson.content:
            lesson.content = lesson.media_items[0].get('url', '')
            lesson.save(update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0030_lesson_media_items'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
