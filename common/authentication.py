"""Authentication classes shared across the API."""

from rest_framework.authentication import BasicAuthentication


class NonPromptingBasicAuthentication(BasicAuthentication):
    """Identical to DRF's BasicAuthentication, except the WWW-Authenticate
    header it advertises on a 401 doesn't start with "Basic".

    This class exists purely so unauthenticated requests get a 401 (not a
    403) — DRF only does that when some authenticator's authenticate_header()
    returns a truthy value, and this is first in DEFAULT_AUTHENTICATION_CLASSES
    for that reason (see base.py). But browsers that see a literal
    `WWW-Authenticate: Basic` header on an XHR/fetch response pop up a
    native username/password dialog, which breaks the frontend's own
    session-based login (it calls GET /auth/me/ on every page load to check
    for an existing session). Any header value that isn't a scheme name a
    browser recognizes (Basic/Digest/Negotiate/NTLM) satisfies DRF's
    truthiness check without triggering that prompt.
    """

    def authenticate_header(self, request):
        return "Session"
