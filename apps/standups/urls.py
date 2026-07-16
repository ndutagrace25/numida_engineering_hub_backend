from django.urls import path

from apps.standups.views import StandupDetailView, StandupListCreateView

urlpatterns = [
    path("", StandupListCreateView.as_view(), name="standup-list-create"),
    path("<int:pk>/", StandupDetailView.as_view(), name="standup-detail"),
]
