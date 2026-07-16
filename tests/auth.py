"""Authentication helper for API tests. No app-specific login flow lives here —
that belongs to the accounts app once it exists.
"""


def authenticate(client, user):
    client.force_authenticate(user=user)
    return client
