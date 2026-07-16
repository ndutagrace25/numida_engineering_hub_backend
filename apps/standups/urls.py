from django.urls import path

from apps.standups.views import StandupCreateView, StandupUpdateDeleteView

urlpatterns = [
    path("", StandupCreateView.as_view(), name="standup-create"),
    path("<int:pk>/", StandupUpdateDeleteView.as_view(), name="standup-update-delete"),
]
