from django.urls import path

from apps.pto.views import PTOEntryDetailView, PTOEntryListCreateView

urlpatterns = [
    path("", PTOEntryListCreateView.as_view(), name="pto-list-create"),
    path("<int:pk>/", PTOEntryDetailView.as_view(), name="pto-detail"),
]
