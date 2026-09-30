"""
URL configuration for the conversations API.
"""

from django.urls import path
from conversations.views import ChatAPIView

app_name = "conversations"

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
]
