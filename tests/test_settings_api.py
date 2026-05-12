import base64
import os
import tempfile
import unittest

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "super-secret-admin-password")
os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("SESSION_HTTPS_ONLY", "0")
os.environ.setdefault("STOCKWORKS_DATA_DIR", tempfile.mkdtemp(prefix="stockworks-settings-test-"))

from fastapi.testclient import TestClient

from app.api import app


class RuntimeSettingsApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        token = base64.b64encode(b"admin:super-secret-admin-password").decode("ascii")
        self.headers = {"Authorization": f"Basic {token}"}

    def test_can_store_and_read_runtime_settings_with_redacted_secrets(self):
        response = self.client.patch(
            "/settings/runtime",
            headers=self.headers,
            json={
                "PRINTLAB_BASE_URL": "http://printlab:8080",
                "PRINTLAB_API_KEY": "abcdef123456",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/settings/runtime", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        settings = response.json()["settings"]
        self.assertEqual(settings["PRINTLAB_BASE_URL"]["value"], "http://printlab:8080")
        self.assertEqual(settings["PRINTLAB_API_KEY"]["value"], "********3456")

    def test_rejects_unknown_runtime_setting(self):
        response = self.client.patch(
            "/settings/runtime",
            headers=self.headers,
            json={"UNSUPPORTED": "value"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
