import base64
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "super-secret-admin-password")
os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("SESSION_HTTPS_ONLY", "0")
os.environ.setdefault("STOCKWORKS_DATA_DIR", tempfile.mkdtemp(prefix="stockworks-docs-test-"))

from fastapi.testclient import TestClient

from app.api import app
from app.business_docs import BusinessDocumentScan


class BusinessDocumentsApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        token = base64.b64encode(b"admin:super-secret-admin-password").decode("ascii")
        self.headers = {"Authorization": f"Basic {token}"}

    def test_uploads_pdf_and_lists_business_document(self):
        scanned = BusinessDocumentScan(
            vendor="Acme Filament Supply",
            receipt_date="2026-05-12",
            total="$143.27",
            display_name="Acme Filament Supply - 2026-05-12 - $143.27",
        )

        with patch("app.api.scan_business_document_pdf", return_value=scanned):
            response = self.client.post(
                "/business-documents/upload",
                headers=self.headers,
                files={"document_pdf": ("receipt.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
            )

        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["display_name"], "Acme Filament Supply - 2026-05-12 - $143.27")
        self.assertEqual(created["vendor"], "Acme Filament Supply")
        self.assertEqual(created["receipt_date"], "2026-05-12")
        self.assertEqual(created["total"], "$143.27")
        self.assertEqual(created["source_filename"], "receipt.pdf")

        response = self.client.get("/business-documents", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        listed = response.json()
        self.assertEqual(listed[0]["display_name"], "Acme Filament Supply - 2026-05-12 - $143.27")

        response = self.client.get(f"/business-documents/{created['id']}/file", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response.headers["content-disposition"])
        self.assertIn("receipt.pdf", response.headers["content-disposition"])

        response = self.client.get(f"/business-documents/{created['id']}/file?download=1", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("receipt.pdf", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
