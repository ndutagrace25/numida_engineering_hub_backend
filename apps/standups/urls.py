from django.urls import path

from apps.standups.views import (
    MyStandupsListView,
    StandupDetailView,
    StandupListCreateView,
    WeeklyStandupsListView,
)

urlpatterns = [
    path("", StandupListCreateView.as_view(), name="standup-list-create"),
    path("mine/", MyStandupsListView.as_view(), name="standup-mine"),
    path("weekly/", WeeklyStandupsListView.as_view(), name="standup-weekly"),
    path("<int:pk>/", StandupDetailView.as_view(), name="standup-detail"),
]
