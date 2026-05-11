from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app import database
from app.config import Settings
from app.repository import insert_snapshot, latest_snapshot_for
from app.services.market_data import MarketDataClient


class SnapshotSerializationTest(unittest.TestCase):
    def test_insert_snapshot_accepts_non_json_raw_data_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database.settings = Settings(database_path=str(Path(tmp_dir) / "test.db"))
            database.init_db()

            snapshot_id = insert_snapshot(
                {
                    "code": "513100",
                    "name": "纳指ETF",
                    "price": 1.23,
                    "source": "unit-test",
                    "raw_data": {
                        "trade_date": date(2026, 5, 11),
                        "created_at": datetime(2026, 5, 11, 9, 30),
                        "pandas_time": pd.Timestamp("2026-05-11 10:00:00"),
                        "nav": Decimal("1.2345"),
                    },
                }
            )

            self.assertGreater(snapshot_id, 0)
            row = latest_snapshot_for("513100")
            self.assertIsNotNone(row)
            raw_data = json.loads(row["raw_data"])
            self.assertEqual(raw_data["trade_date"], "2026-05-11")
            self.assertEqual(raw_data["created_at"], "2026-05-11 09:30:00")
            self.assertEqual(raw_data["pandas_time"], "2026-05-11 10:00:00")
            self.assertEqual(raw_data["nav"], "1.2345")

    def test_safe_val_normalizes_common_market_data_types(self) -> None:
        cleaned = MarketDataClient._safe_val(
            {
                "date": date(2026, 5, 11),
                "timestamp": pd.Timestamp("2026-05-11 10:00:00"),
                "missing_time": pd.NaT,
                "decimal": Decimal("1.2345"),
                "nan_decimal": Decimal("NaN"),
            }
        )

        self.assertEqual(cleaned["date"], "2026-05-11")
        self.assertEqual(cleaned["timestamp"], "2026-05-11T10:00:00")
        self.assertIsNone(cleaned["missing_time"])
        self.assertEqual(cleaned["decimal"], 1.2345)
        self.assertIsNone(cleaned["nan_decimal"])


if __name__ == "__main__":
    unittest.main()
