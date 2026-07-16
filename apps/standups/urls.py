from django.urls import path

from apps.standups.views import StandupCreateView

urlpatterns = [
    path("", StandupCreateView.as_view(), name="standup-create"),
]
