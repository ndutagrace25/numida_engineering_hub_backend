from django.urls import path

from apps.standups.views import StandupCreateView, StandupUpdateView

urlpatterns = [
    path("", StandupCreateView.as_view(), name="standup-create"),
    path("<int:pk>/", StandupUpdateView.as_view(), name="standup-update"),
]
