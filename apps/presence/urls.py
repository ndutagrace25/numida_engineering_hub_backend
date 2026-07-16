from django.urls import path

from apps.presence.views import HeartbeatView, UserPresenceListView

urlpatterns = [
    path("", UserPresenceListView.as_view(), name="presence-list"),
    path("heartbeat/", HeartbeatView.as_view(), name="presence-heartbeat"),
]
