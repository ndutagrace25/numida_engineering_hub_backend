from django.urls import path

from apps.presence.views import HeartbeatView

urlpatterns = [
    path("heartbeat/", HeartbeatView.as_view(), name="presence-heartbeat"),
]
