"""
Serializers for the conversations API.
"""

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """
    Validates user chat requests sent to /api/chat/.
    """

    query = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "The 'query' field is required.",
            "blank": "The 'query' field cannot be empty or whitespace only.",
        },
    )
    conversation_id = serializers.CharField(
        required=False,
        allow_blank=False,
        allow_null=True,
        default=None,
    )
    session_id = serializers.CharField(
        required=False,
        allow_blank=False,
        allow_null=True,
        default=None,
    )

    def validate_query(self, value: str) -> str:
        """Ensure query is non-empty after stripping whitespace."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "The 'query' field cannot be empty or whitespace only."
            )
        return value.strip()
