from django.urls import reverse

from hub.models import Activity, Resource

from .test_collaborators import CollaboratorBase


class AuthoringResourceTests(CollaboratorBase):
    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(module=self.module1, title='A', order=1)

    def _create_url(self):
        return reverse('authoring-resource-create', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': self.activity.pk})

    def _detail_url(self, resource):
        return reverse('authoring-resource-detail', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk,
            'lesson_pk': self.activity.pk, 'resource_pk': resource.pk})

    def _mk(self, **kw):
        kw.setdefault('type', 'text')
        kw.setdefault('order', kw.get('order', Resource.objects.filter(activity=self.activity).count() + 1))
        return Resource.objects.create(activity=self.activity, **kw)

    def test_author_creates_resource(self):
        self._login_as(self.creator)
        res = self.client.post(self._create_url(), {'type': 'text', 'content': 'hi'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.activity.resources.count(), 1)

    def test_non_author_cannot_create(self):
        self._login_as(self.other_creator)
        res = self.client.post(self._create_url(), {'type': 'text', 'content': 'x'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_co_editor_can_create(self):
        self._add(self.other_creator, 'co_editor')
        self._login_as(self.other_creator)
        res = self.client.post(self._create_url(), {'type': 'text', 'content': 'x'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_translator_cannot_create_source_resource(self):
        self._add(self.other_creator, 'translator')
        self._login_as(self.other_creator)
        res = self.client.post(self._create_url(), {'type': 'text', 'content': 'x'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_translator_can_edit_translation(self):
        r = self._mk(content='hello')
        self._add(self.other_creator, 'translator')
        self._login_as(self.other_creator)
        res = self.client.patch(f'{self._detail_url(r)}?lang=el', {'content': 'γεια'}, format='json')
        self.assertEqual(res.status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.translations['el']['content'], 'γεια')

    def test_translator_cannot_edit_source(self):
        r = self._mk(content='hello')
        self._add(self.other_creator, 'translator')
        self._login_as(self.other_creator)
        res = self.client.patch(self._detail_url(r), {'content': 'hacked'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_author_deletes_resource(self):
        r = self._mk()
        self._login_as(self.creator)
        res = self.client.delete(self._detail_url(r))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Resource.objects.filter(pk=r.pk).exists())

    def test_reorder(self):
        r1 = self._mk(order=1)
        r2 = self._mk(order=2)
        self._login_as(self.creator)
        url = reverse('authoring-resource-reorder', kwargs={
            'pk': self.course.pk, 'module_pk': self.module1.pk, 'lesson_pk': self.activity.pk})
        res = self.client.patch(url, {'order': [r2.pk, r1.pk]}, format='json')
        self.assertEqual(res.status_code, 200)
        r1.refresh_from_db()
        r2.refresh_from_db()
        self.assertEqual((r2.order, r1.order), (1, 2))

    def test_translated_quiz_must_keep_shape(self):
        quiz = self._mk(type='quiz', quiz_data=[{'question': 'Q', 'options': [
            {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}])
        self._login_as(self.creator)
        bad = [{'question': 'Κ', 'options': [{'text': 'α'}, {'text': 'β'}, {'text': 'γ'}]}]
        res = self.client.patch(f'{self._detail_url(quiz)}?lang=el', {'quiz_data': bad}, format='json')
        self.assertEqual(res.status_code, 400)
        good = [{'question': 'Κ', 'options': [{'text': 'α'}, {'text': 'β'}]}]
        res = self.client.patch(f'{self._detail_url(quiz)}?lang=el', {'quiz_data': good}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_new_and_edited_resources_are_resynced_to_translated_languages(self):
        from unittest.mock import patch
        self.course.translation_status = {'el': 'done'}
        self.course.save(update_fields=['translation_status'])
        self._login_as(self.creator)
        with patch('hub.tasks.translate_resource_meta.delay') as delay:
            res = self.client.post(self._create_url(), {'type': 'text', 'content': 'hi'}, format='json')
            delay.assert_called_once_with(res.data['id'], 'el')
            delay.reset_mock()
            resource = Resource.objects.get(pk=res.data['id'])
            self.client.patch(self._detail_url(resource), {'is_required': False}, format='json')
            delay.assert_not_called()  # no translatable change
            self.client.patch(self._detail_url(resource), {'content': 'changed'}, format='json')
            delay.assert_called_once_with(resource.id, 'el')


class ResourceMachineTranslationTests(CollaboratorBase):
    def test_translate_course_translates_resources(self):
        from unittest.mock import patch

        from hub.tasks import translate_course
        activity = Activity.objects.create(module=self.module1, title='A', order=1)
        text = Resource.objects.create(activity=activity, type='text', order=1, content='Body')
        video = Resource.objects.create(activity=activity, type='video', order=2,
                                        url='https://v.example/x', caption='Cap')
        quiz = Resource.objects.create(activity=activity, type='quiz', order=3, quiz_data=[
            {'question': 'Q?', 'options': [{'text': 'A', 'is_correct': True},
                                           {'text': 'B', 'is_correct': False}]}])
        with patch('hub.tasks.translate_text', side_effect=lambda t, s, d: f'[{d}] {t}'):
            translate_course(self.course.id, 'el')
        for r in (text, video, quiz):
            r.refresh_from_db()
        self.assertEqual(text.translations['el']['content'], '[el] Body')
        self.assertEqual(video.translations['el'], {'caption': '[el] Cap'})  # URL untouched
        self.assertEqual(quiz.translations['el']['quiz_data'][0]['options'][0],
                         {'text': '[el] A', 'is_correct': True})
