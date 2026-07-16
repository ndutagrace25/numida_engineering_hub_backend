from django.urls import path

from apps.accounts.views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    UserDetailView,
    UserListView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
]
