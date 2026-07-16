from django.urls import path

from apps.aob.views import AOBItemDetailView, AOBItemListCreateView

urlpatterns = [
    path("", AOBItemListCreateView.as_view(), name="aob-item-list-create"),
    path("<int:pk>/", AOBItemDetailView.as_view(), name="aob-item-detail"),
]
