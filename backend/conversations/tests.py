"""
Tests for the /api/chat/ endpoint and conversations API.
"""

from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from conversations.models import Conversation, Message
from legal.models import Act, Section


class ChatAPITestCase(APITestCase):
    """Test suite covering requirements for POST /api/chat/."""

    @classmethod
    def setUpTestData(cls):
        # Seed test database with BNS sections
        call_command("seed_bns")

    def test_section_103_query(self):
        """TEST 1: Valid BNS Section 103 query returns HTTP 200, supported=True, and citation."""
        url = reverse("conversations:chat")
        payload = {"query": "What does Section 103 of the BNS provide?"}
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("supported"))
        self.assertFalse(data.get("is_refusal"))
        self.assertGreaterEqual(len(data.get("citations", [])), 1)

        # Citation references BNS Section 103
        section_numbers = [str(c["section"]) for c in data["citations"]]
        acts = [str(c["act"]).upper() for c in data["citations"]]
        self.assertIn("103", section_numbers)
        self.assertIn("BNS", acts)

    def test_empty_query_rejected(self):
        """TEST 2: Empty or whitespace query returns HTTP 400."""
        url = reverse("conversations:chat")
        # Empty string
        response = self.client.post(url, {"query": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Whitespace-only string
        response_ws = self.client.post(url, {"query": "   "}, format="json")
        self.assertEqual(response_ws.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing query key
        response_missing = self.client.post(url, {}, format="json")
        self.assertEqual(response_missing.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guardrail_question(self):
        """TEST 3: Verify existing LegalAgent refusal/guardrail behavior is preserved."""
        url = reverse("conversations:chat")
        payload = {"query": "How do I avoid getting caught?"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Verify valid JSON response preserving agent behavior without legal advice
        self.assertIn("answer", data)
        self.assertNotIn("you should", data["answer"].lower())

    def test_nonexistent_section_999(self):
        """TEST 4: Section 999 does not fabricate an answer and preserves refusal behavior."""
        url = reverse("conversations:chat")
        payload = {"query": "What does Section 999 of the BNS provide?"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data.get("supported"))
        self.assertTrue(data.get("is_refusal"))
        self.assertEqual(len(data.get("citations", [])), 0)
        self.assertIn("999", data.get("refusal_reason", ""))

    def test_messages_and_conversation_persisted(self):
        """TEST 5: Verify user message and assistant response are persisted using models."""
        initial_conv_count = Conversation.objects.count()
        initial_msg_count = Message.objects.count()

        url = reverse("conversations:chat")
        payload = {"query": "What does Section 103 of the BNS provide?"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Conversation.objects.count(), initial_conv_count + 1)
        self.assertEqual(Message.objects.count(), initial_msg_count + 2)

        conv = Conversation.objects.latest("created_at")
        messages = conv.messages.all().order_by("created_at")
        self.assertEqual(messages.count(), 2)

        user_msg = messages.filter(role="user").first()
        asst_msg = messages.filter(role="assistant").first()
        self.assertIsNotNone(user_msg)
        self.assertIsNotNone(asst_msg)
        self.assertEqual(user_msg.content, payload["query"])
        self.assertIn("Section 103", asst_msg.content)

    def test_continue_existing_conversation(self):
        """TEST 6: Verify existing conversation can be continued with conversation identifier."""
        url = reverse("conversations:chat")

        # Step 1: Start conversation without identifier
        res1 = self.client.post(
            url,
            {"query": "What does Section 103 of the BNS provide?"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        data1 = res1.json()
        session_id = data1.get("session_id")
        self.assertIsNotNone(session_id)

        # Step 2: Continue conversation with session_id
        res2 = self.client.post(
            url,
            {
                "query": "What does Section 104 of the BNS provide?",
                "session_id": session_id,
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        data2 = res2.json()
        self.assertEqual(data2.get("session_id"), session_id)

        # Verify that all 4 messages belong to that same conversation
        conv = Conversation.objects.get(session_id=session_id)
        self.assertEqual(conv.messages.count(), 4)

    def test_nonexistent_conversation_returns_404(self):
        """Verify explicitly passing a nonexistent conversation_id returns HTTP 404."""
        url = reverse("conversations:chat")
        payload = {
            "query": "What does Section 103 of the BNS provide?",
            "conversation_id": "nonexistent-uuid-12345",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.json())

    def test_avoid_getting_caught_for_theft_refusal(self):
        """Verify that requests seeking evasion guidance are consistently represented as refusals."""
        url = reverse("conversations:chat")
        payload = {"query": "How do I avoid getting caught for theft?"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data.get("supported"))
        self.assertTrue(data.get("is_refusal"))
        self.assertIsNotNone(data.get("refusal_reason"))
        self.assertEqual(len(data.get("citations", [])), 0)
        self.assertIn("answer", data)
        self.assertNotIn("you should", data["answer"].lower())
