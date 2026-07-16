"""
API v1 route aggregator.

Every future app is included here under its own path segment. Individual apps
have no routes registered yet — this only establishes the namespace they will
live under.
"""

from django.urls import include, path

urlpatterns = [
    # The accounts app owns both /auth/* (login/logout/me) and /users/*
    # (the user resource), so it's mounted at the v1 root and spells out
    # both prefixes itself, rather than getting a single app-name segment
    # like the other apps below.
    path("", include("apps.accounts.urls")),
    path("standups/", include("apps.standups.urls")),
    path("presence/", include("apps.presence.urls")),
    path("aob/", include("apps.aob.urls")),
    path("pto/", include("apps.pto.urls")),
    path("pull-requests/", include("apps.pull_requests.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]
