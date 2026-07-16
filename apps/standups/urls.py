from django.urls import path

from apps.standups.views import StandupCreateView, StandupDetailView

urlpatterns = [
    path("", StandupCreateView.as_view(), name="standup-create"),
    path("<int:pk>/", StandupDetailView.as_view(), name="standup-detail"),
]
