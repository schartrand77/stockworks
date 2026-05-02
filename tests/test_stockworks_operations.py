import unittest
import base64
import re
from pathlib import Path

from app.authz import Actor, resolve_actor, role_can
from app.csv_tools import export_material_rows, parse_material_csv
from app.email_digest import LowStockEntry, build_low_stock_digest, smtp_config_from_env
from app.printlab import PrintLabClient


class AuthzTests(unittest.TestCase):
    def test_resolves_shop_actor_from_credentials(self):
        actor = resolve_actor(
            "floor",
            "floor-password",
            admin_username="admin",
            admin_email="",
            admin_password="admin-password",
            shop_username="floor",
            shop_email="floor@example.com",
            shop_password="floor-password",
        )
        self.assertEqual(actor, Actor(username="floor", role="shop"))

    def test_shop_cannot_delete_materials(self):
        self.assertFalse(role_can("shop", "materials:delete"))
        self.assertTrue(role_can("admin", "materials:delete"))


class CsvToolTests(unittest.TestCase):
    def test_parse_material_csv_reports_row_errors_and_valid_rows(self):
        content = (
            "name,filament_type,color,price_per_gram,spool_weight_grams\n"
            "PLA,PLA,Black,0.02,1000\n"
            "Bad,PLA,Red,nope,1000\n"
        )
        result = parse_material_csv(content.encode("utf-8"))
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.errors[0]["row"], 3)

    def test_export_material_rows_includes_expected_header(self):
        csv_text = export_material_rows([])
        self.assertTrue(csv_text.startswith("name,brand,filament_type,category,color"))


class EmailDigestTests(unittest.TestCase):
    def test_digest_contains_filament_and_hardware(self):
        digest = build_low_stock_digest(
            filament=[
                LowStockEntry(name="PLA Black", location="Rack A", quantity=100, reorder_level=500, unit="g"),
            ],
            hardware=[
                LowStockEntry(name="M3 Inserts", location="Bin 1", quantity=4, reorder_level=20, unit="piece"),
            ],
        )
        self.assertIn("PLA Black", digest.text)
        self.assertIn("M3 Inserts", digest.html)

    def test_smtp_config_requires_core_values(self):
        env = {"SMTP_HOST": "smtp.example.com", "LOW_STOCK_DIGEST_RECIPIENTS": "ops@example.com"}
        self.assertIsNone(smtp_config_from_env(env))


class PrintLabClientTests(unittest.TestCase):
    def test_builds_basic_auth_header_from_username_and_password(self):
        client = PrintLabClient(
            base_url="http://printlab:8080",
            username="admin",
            password="secret",
        )

        headers = client._build_request_headers()

        expected = base64.b64encode(b"admin:secret").decode("ascii")
        self.assertEqual(headers["Authorization"], f"Basic {expected}")


class StaticAssetTests(unittest.TestCase):
    def test_ams_slots_use_compact_dimensions_for_many_printers(self):
        css = Path("app/static/styles.css").read_text(encoding="utf-8")

        grid_rule = re.search(r"\.ams-slot-grid\s*\{(?P<body>[^}]*)\}", css, re.S)
        spool_rule = re.search(r"\.ams-slot-spool\s*\{(?P<body>[^}]*)\}", css, re.S)
        self.assertIsNotNone(grid_rule)
        self.assertIsNotNone(spool_rule)

        min_track = re.search(r"minmax\((?P<size>\d+)px,\s*1fr\)", grid_rule.group("body"))
        spool_width = re.search(r"width:\s*(?P<size>\d+)px", spool_rule.group("body"))
        self.assertIsNotNone(min_track)
        self.assertIsNotNone(spool_width)
        self.assertLessEqual(int(min_track.group("size")), 112)
        self.assertLessEqual(int(spool_width.group("size")), 38)


if __name__ == "__main__":
    unittest.main()
