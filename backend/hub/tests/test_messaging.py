from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import Conversation, Message, UserProfile


def make_user(username, first='F', last='L'):
    u = User.objects.create_user(username=username, password='pass12345',
                                 first_name=first, last_name=last)
    UserProfile.objects.create(user=u, user_type=UserProfile.UserType.TEACHER, avatar_initials='XX')
    return u


class MessagingTests(APITestCase):
    def setUp(self):
        self.alice = make_user('alice', 'Alice', 'A')
        self.bob = make_user('bob', 'Bob', 'B')
        self.carol = make_user('carol', 'Carol', 'C')

    def _send(self, sender, to, text):
        self.client.force_authenticate(sender)
        return self.client.post(f'/api/messages/with/{to.id}/', {'text': text}, format='json')

    def test_send_creates_conversation_and_message(self):
        res = self._send(self.alice, self.bob, 'Hello Bob')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['is_mine'])
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)

    def test_same_pair_reuses_one_conversation(self):
        self._send(self.alice, self.bob, 'hi')
        self._send(self.bob, self.alice, 'hey back')
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 2)

    def test_cannot_message_self(self):
        res = self._send(self.alice, self.alice, 'note to self')
        self.assertEqual(res.status_code, 400)

    def test_empty_text_rejected(self):
        res = self._send(self.alice, self.bob, '   ')
        self.assertEqual(res.status_code, 400)

    def test_conversation_list_shows_preview_and_unread(self):
        self._send(self.bob, self.alice, 'first')
        self._send(self.bob, self.alice, 'second')
        self.client.force_authenticate(self.alice)
        rows = self.client.get('/api/messages/conversations/').data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['last_message'], 'second')
        self.assertEqual(rows[0]['unread_count'], 2)
        self.assertEqual(rows[0]['other_user']['name'], 'Bob B')

    def test_opening_thread_marks_read(self):
        self._send(self.bob, self.alice, 'unread msg')
        self.assertEqual(self._unread(self.alice), 1)
        self.client.force_authenticate(self.alice)
        self.client.get(f'/api/messages/with/{self.bob.id}/')
        self.assertEqual(self._unread(self.alice), 0)

    def _unread(self, user):
        self.client.force_authenticate(user)
        return self.client.get('/api/messages/unread-count/').data['unread']

    def test_unread_count_excludes_own_messages(self):
        self._send(self.alice, self.bob, 'mine')
        self.assertEqual(self._unread(self.alice), 0)
        self.assertEqual(self._unread(self.bob), 1)

    def test_list_search_filters_by_name(self):
        self._send(self.bob, self.alice, 'hi')
        self._send(self.carol, self.alice, 'hi')
        self.client.force_authenticate(self.alice)
        rows = self.client.get('/api/messages/conversations/?search=carol').data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['other_user']['name'], 'Carol C')

    def test_empty_conversation_not_listed(self):
        # A thread fetched but never sent to should not clutter the list.
        self.client.force_authenticate(self.alice)
        self.client.get(f'/api/messages/with/{self.bob.id}/')
        rows = self.client.get('/api/messages/conversations/').data
        self.assertEqual(rows, [])

    def test_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/messages/conversations/').status_code, 401)
