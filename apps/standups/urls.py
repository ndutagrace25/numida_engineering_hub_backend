from django.urls import path

from apps.standups.views import MyStandupsListView, StandupDetailView, StandupListCreateView

urlpatterns = [
    path("", StandupListCreateView.as_view(), name="standup-list-create"),
    path("mine/", MyStandupsListView.as_view(), name="standup-mine"),
    path("<int:pk>/", StandupDetailView.as_view(), name="standup-detail"),
]
