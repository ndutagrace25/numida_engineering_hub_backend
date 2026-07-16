"""Base test class future feature tests should inherit from."""

from rest_framework.test import APITestCase

from tests.auth import authenticate
from tests.helpers import get_data, get_error


class BaseAPITestCase(APITestCase):
    def authenticate(self, user):
        return authenticate(self.client, user)

    def get_data(self, response):
        return get_data(response)

    def get_error(self, response):
        return get_error(response)
