import unittest

from app.settings import (
    get_effective_setting,
    mask_secret,
    redact_settings,
    validate_settings_payload,
)


class RuntimeSettingsTests(unittest.TestCase):
    def test_env_remains_fallback_for_missing_stored_value(self):
        self.assertEqual(
            get_effective_setting(
                "PRINTLAB_BASE_URL",
                {},
                env={"PRINTLAB_BASE_URL": "http://printlab:8080"},
            ),
            "http://printlab:8080",
        )

    def test_stored_value_overrides_env(self):
        self.assertEqual(
            get_effective_setting(
                "PRINTLAB_BASE_URL",
                {"PRINTLAB_BASE_URL": "http://localhost:8080"},
                env={"PRINTLAB_BASE_URL": "http://printlab:8080"},
            ),
            "http://localhost:8080",
        )

    def test_masks_secret_values(self):
        self.assertEqual(mask_secret("abcdef123456"), "********3456")
        redacted = redact_settings({"PRINTLAB_API_KEY": "abcdef123456"})
        self.assertEqual(redacted["PRINTLAB_API_KEY"]["value"], "********3456")
        self.assertTrue(redacted["PRINTLAB_API_KEY"]["secret"])

    def test_rejects_unknown_setting_keys(self):
        with self.assertRaises(ValueError):
            validate_settings_payload({"NOT_ALLOWED": "value"})


if __name__ == "__main__":
    unittest.main()
