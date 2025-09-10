from django.urls import path

from app import consumers

websocket_urlpatterns = [
    path('ws/logs/<int:log_id>', consumers.LogConsumer.as_asgi())
]