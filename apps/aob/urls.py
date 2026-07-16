from django.urls import path

from apps.aob.views import AOBItemCreateView, AOBItemDetailView

urlpatterns = [
    path("", AOBItemCreateView.as_view(), name="aob-item-create"),
    path("<int:pk>/", AOBItemDetailView.as_view(), name="aob-item-detail"),
]
