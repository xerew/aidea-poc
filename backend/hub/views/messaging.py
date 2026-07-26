from django.contrib.auth.models import User
from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import Conversation, Message
from hub.serializers.messaging import (
    ConversationListSerializer,
    MessageSerializer,
    user_brief,
)


class ConversationListView(APIView):
    """GET /api/messages/conversations/?search= — my conversations, newest first."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        me = request.user
        conversations = (
            Conversation.objects.filter(Q(user_a=me) | Q(user_b=me))
            .select_related('user_a__profile', 'user_b__profile')
            .prefetch_related(Prefetch('messages', queryset=Message.objects.order_by('created_at')))
            .order_by('-updated_at')
        )

        search = request.query_params.get('search', '').strip().lower()
        rows = list(conversations)
        # Drop empty conversations (created but never sent to) from the list.
        rows = [c for c in rows if c.messages.all()]
        if search:
            def matches(conv):
                other = conv.other_user(me)
                name = (other.get_full_name() or other.username).lower()
                return search in name
            rows = [c for c in rows if matches(c)]

        data = ConversationListSerializer(rows, many=True, context={'request': request}).data
        return Response(data)


class ConversationDetailView(APIView):
    """Thread with one user, keyed by that user's id.

    GET  /api/messages/with/<user_id>/  — messages (marks incoming as read).
    POST /api/messages/with/<user_id>/  — send {text}.
    """
    permission_classes = [IsAuthenticated]

    def _get_other(self, request, user_id):
        if user_id == request.user.id:
            return None, Response(
                {'detail': 'You cannot message yourself.'}, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return User.objects.select_related('profile').get(pk=user_id), None
        except User.DoesNotExist:
            return None, Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, user_id):
        other, err = self._get_other(request, user_id)
        if err:
            return err

        conv = Conversation.objects.filter(
            Q(user_a=request.user, user_b=other) | Q(user_a=other, user_b=request.user),
        ).first()

        messages = []
        if conv:
            # Mark the other person's unread messages as read.
            conv.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(
                read_at=timezone.now(),
            )
            messages = conv.messages.all()

        return Response({
            'other_user': user_brief(other, request),
            'messages': MessageSerializer(messages, many=True, context={'request': request}).data,
        })

    def post(self, request, user_id):
        other, err = self._get_other(request, user_id)
        if err:
            return err

        text = str(request.data.get('text', '')).strip()
        if not text:
            return Response({'detail': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        conv = Conversation.between(request.user, other)
        message = Message.objects.create(conversation=conv, sender=request.user, text=text)
        Conversation.objects.filter(pk=conv.pk).update(updated_at=timezone.now())

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class UnreadMessageCountView(APIView):
    """GET /api/messages/unread-count/ — total unread across my conversations."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            Q(conversation__user_a=request.user) | Q(conversation__user_b=request.user),
            read_at__isnull=True,
        ).exclude(sender=request.user).count()
        return Response({'unread': count})
