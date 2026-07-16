from django.urls import path

from apps.aob.views import AOBItemCreateView

urlpatterns = [
    path("", AOBItemCreateView.as_view(), name="aob-item-create"),
]
