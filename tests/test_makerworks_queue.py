import json
import unittest

from sqlalchemy import create_engine, text
from sqlmodel import Session

from app.makerworks_queue import list_makerworks_production_jobs


class MakerWorksQueueTests(unittest.TestCase):
    def test_lists_queued_and_completed_printlab_jobs_from_makerworks_tables(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE "PrintOrder" (
                        id TEXT PRIMARY KEY,
                        "orderNumber" INTEGER,
                        status TEXT,
                        "customerEmail" TEXT,
                        "customerName" TEXT,
                        "paymentMethod" TEXT,
                        "paymentStatus" TEXT,
                        "totalCents" INTEGER,
                        currency TEXT,
                        metadata TEXT,
                        "printerId" TEXT,
                        "createdAt" TEXT,
                        "updatedAt" TEXT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE "PrintOrderItem" (
                        id TEXT PRIMARY KEY,
                        "orderId" TEXT,
                        "modelTitle" TEXT,
                        material TEXT,
                        quantity INTEGER,
                        "totalCents" INTEGER
                    )
                    """
                )
            )
            conn.execute(text('CREATE TABLE "Printer" (id TEXT PRIMARY KEY, name TEXT)'))
            conn.execute(
                text(
                    """
                    INSERT INTO "Printer" (id, name)
                    VALUES ('printer-1', 'Bambu A1')
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO "PrintOrder" (
                        id, "orderNumber", status, "customerEmail", "customerName",
                        "paymentMethod", "paymentStatus", "totalCents", currency,
                        metadata, "printerId", "createdAt", "updatedAt"
                    )
                    VALUES
                    (
                        'order-queued', 42, 'queued', 'buyer@example.com', 'Buyer',
                        'card', 'paid', 2500, 'USD', :queued_metadata,
                        'printer-1', '2026-05-01T10:00:00Z', '2026-05-01T10:00:00Z'
                    ),
                    (
                        'order-completed', 43, 'completed', 'done@example.com', 'Done',
                        'card', 'paid', 1500, 'USD', :completed_metadata,
                        NULL, '2026-05-02T10:00:00Z', '2026-05-02T10:00:00Z'
                    ),
                    (
                        'order-awaiting-review', 44, 'awaiting_review', 'skip@example.com', 'Skip',
                        'card', 'pending', 1500, 'USD', '{}',
                        NULL, '2026-05-03T10:00:00Z', '2026-05-03T10:00:00Z'
                    )
                    """
                ),
                {
                    "queued_metadata": json.dumps(
                        {
                            "lastPrintLabSubmission": {
                                "status": "queued",
                                "printerName": "Bambu A1",
                                "printLabJobId": "pl-100",
                            }
                        }
                    ),
                    "completed_metadata": json.dumps(
                        {
                            "lastPrintLabSubmission": {
                                "status": "completed",
                                "printerName": "Bambu X1",
                                "printLabJobId": "pl-101",
                            }
                        }
                    ),
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO "PrintOrderItem" (id, "orderId", "modelTitle", material, quantity, "totalCents")
                    VALUES
                    ('item-1', 'order-queued', 'Widget', 'PLA', 2, 2500),
                    ('item-2', 'order-completed', 'Bracket', 'PETG', 1, 1500)
                    """
                )
            )

        with Session(engine) as session:
            jobs = list_makerworks_production_jobs(session)

        self.assertEqual([job["id"] for job in jobs], ["order-queued", "order-completed"])
        self.assertEqual(jobs[0]["orderLabel"], "MW-00042")
        self.assertEqual(jobs[0]["status"], "queued")
        self.assertEqual(jobs[0]["printLabStatus"], "queued")
        self.assertEqual(jobs[0]["printLabPrinterName"], "Bambu A1")
        self.assertEqual(jobs[0]["printerName"], "Bambu A1")
        self.assertEqual(jobs[0]["lineItems"], [{"modelTitle": "Widget", "material": "PLA", "quantity": 2, "totalCents": 2500}])
        self.assertEqual(jobs[1]["status"], "completed")
        self.assertEqual(jobs[1]["printLabJobId"], "pl-101")


if __name__ == "__main__":
    unittest.main()
