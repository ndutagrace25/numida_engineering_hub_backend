from django.urls import path

from apps.aob.views import AOBItemCreateView, AOBItemUpdateDeleteView

urlpatterns = [
    path("", AOBItemCreateView.as_view(), name="aob-item-create"),
    path("<int:pk>/", AOBItemUpdateDeleteView.as_view(), name="aob-item-update-delete"),
]
