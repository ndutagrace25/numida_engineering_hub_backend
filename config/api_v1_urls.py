"""
API v1 route aggregator.

Every future app is included here under its own path segment. Individual apps
have no routes registered yet — this only establishes the namespace they will
live under.
"""

from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("standups/", include("apps.standups.urls")),
    path("presence/", include("apps.presence.urls")),
    path("aob/", include("apps.aob.urls")),
    path("pto/", include("apps.pto.urls")),
    path("pull-requests/", include("apps.pull_requests.urls")),
]
