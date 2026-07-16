from django.urls import path

from apps.pull_requests.views import PullRequestLinkDetailView, PullRequestLinkListCreateView

urlpatterns = [
    path("", PullRequestLinkListCreateView.as_view(), name="pull-request-link-list-create"),
    path("<int:pk>/", PullRequestLinkDetailView.as_view(), name="pull-request-link-detail"),
]
