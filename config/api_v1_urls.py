"""
API v1 route aggregator.

Every app is included here under its own path segment. A v2 later means
adding config/api_v2_urls.py and including it alongside this one, without
touching these routes.
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
    path("aob-items/", include("apps.aob.urls")),
    path("pto/", include("apps.pto.urls")),
    path("pull-request-links/", include("apps.pull_requests.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]
