"""Direct unit tests for common.logging.JSONFormatter — used in production
only, so nothing in the rest of the suite (which always runs under
config.settings.test's console formatter) exercises it indirectly.
"""

import json
import logging
import sys

from django.test import SimpleTestCase

from common.logging import JSONFormatter


class JSONFormatterTests(SimpleTestCase):
    def _record(self, **overrides):
        defaults = {
            "name": "django.request",
            "level": logging.INFO,
            "pathname": __file__,
            "lineno": 1,
            "msg": "GET /health/ 200",
            "args": (),
            "exc_info": None,
        }
        defaults.update(overrides)
        return logging.LogRecord(**defaults)

    def test_format_returns_valid_json_with_expected_fields(self):
        payload = json.loads(JSONFormatter().format(self._record()))

        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "django.request")
        self.assertEqual(payload["message"], "GET /health/ 200")
        self.assertIn("timestamp", payload)
        self.assertNotIn("exception", payload)

    def test_message_formatting_applies_args(self):
        record = self._record(msg="%s %s %s", args=("GET", "/health/", 200))

        payload = json.loads(JSONFormatter().format(record))

        self.assertEqual(payload["message"], "GET /health/ 200")

    def test_exception_info_is_included_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = self._record(level=logging.ERROR, exc_info=sys.exc_info())

        payload = json.loads(JSONFormatter().format(record))

        self.assertIn("exception", payload)
        self.assertIn("ValueError: boom", payload["exception"])
