"""
Views for the conversations API.
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path so 'ai' package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.agent import LegalAgent
from conversations.models import Conversation, Message
from conversations.serializers import ChatRequestSerializer

logger = logging.getLogger(__name__)

# Module-level agent cache so embedding model is loaded once
_agent: Optional[LegalAgent] = None


def get_agent() -> LegalAgent:
    """Retrieve or initialize the singleton LegalAgent instance."""
    global _agent
    if _agent is None:
        _agent = LegalAgent()
    return _agent


class ChatAPIView(APIView):
    """
    POST /api/chat/

    Accepts a legal query, routes it through LegalAgent, persists the
    user message and assistant response in the database, and returns
    the serialized LegalResponse JSON.
    """

    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        clean_query = serializer.validated_data["query"]
        supplied_session_id = (
            serializer.validated_data.get("conversation_id")
            or serializer.validated_data.get("session_id")
        )

        # 1. Resolve or create Conversation and retrieve previous history
        conversation_history = []
        if supplied_session_id:
            try:
                conversation = Conversation.objects.get(session_id=supplied_session_id)
                # Bounded history (most recent 8 messages, ordered chronologically)
                recent_msgs = list(
                    conversation.messages.order_by("-created_at")[:8]
                )
                recent_msgs.reverse()
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in recent_msgs
                ]
            except Conversation.DoesNotExist:
                return Response(
                    {"error": f"Conversation with ID '{supplied_session_id}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = Conversation.objects.create(session_id=str(uuid.uuid4()))

        # 2. Persist user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=clean_query,
        )

        # 3. Process query with LegalAgent including conversation history
        try:
            agent = get_agent()
            legal_response = agent.ask(clean_query, conversation_history=conversation_history)
        except Exception as err:
            logger.exception("Unexpected error in LegalAgent execution: %s", err)
            return Response(
                {"error": "An internal error occurred while processing your legal request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Persist assistant message
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=legal_response.answer,
        )

        # 5. Serialize LegalResponse to JSON safely
        response_data = legal_response.model_dump()
        response_data["session_id"] = conversation.session_id
        response_data["conversation_id"] = conversation.session_id

        return Response(response_data, status=status.HTTP_200_OK)
