from django.contrib.auth.models import User
from django.db import models


class Conversation(models.Model):
    """A 1:1 thread between two users.

    Participants are stored ordered by id (user_a.id < user_b.id) so each pair
    maps to exactly one row.
    """
    user_a     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_a')
    user_b     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_b')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)  # bumped on each new message

    class Meta:
        unique_together = ('user_a', 'user_b')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user_a.username} ↔ {self.user_b.username}'

    @staticmethod
    def pair(u1, u2):
        """Return the two users ordered by id, ready for user_a/user_b."""
        return (u1, u2) if u1.id < u2.id else (u2, u1)

    @classmethod
    def between(cls, u1, u2):
        """Fetch or create the conversation between two users."""
        a, b = cls.pair(u1, u2)
        conv, _ = cls.objects.get_or_create(user_a=a, user_b=b)
        return conv

    def other_user(self, me):
        return self.user_b if self.user_a_id == me.id else self.user_a


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text         = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)
    read_at      = models.DateTimeField(null=True, blank=True)  # set when the recipient opens the thread

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.username}: {self.text[:40]}'
