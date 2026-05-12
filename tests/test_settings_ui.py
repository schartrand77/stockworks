import unittest
from pathlib import Path


class RuntimeSettingsUiTests(unittest.TestCase):
    def test_settings_panel_contains_suite_runtime_controls(self):
        html = Path("app/templates/index.html").read_text(encoding="utf-8")
        script = Path("app/static/app.js").read_text(encoding="utf-8")

        self.assertIn("PrintLab integration", html)
        self.assertIn("OrderWorks fallback", html)
        self.assertIn("Low-stock email digest", html)
        self.assertIn('id="runtime-settings-save"', html)
        self.assertIn("loadRuntimeSettings", script)
        self.assertIn("saveRuntimeSettings", script)


if __name__ == "__main__":
    unittest.main()
