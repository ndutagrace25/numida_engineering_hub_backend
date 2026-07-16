from django.urls import path

from apps.aob.views import AOBItemCreateView, AOBItemUpdateView

urlpatterns = [
    path("", AOBItemCreateView.as_view(), name="aob-item-create"),
    path("<int:pk>/", AOBItemUpdateView.as_view(), name="aob-item-update"),
]
