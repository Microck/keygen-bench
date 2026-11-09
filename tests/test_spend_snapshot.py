"""Verify the retained Pro receipts are reflected once in the spend snapshot."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web/classic"))
from build_spend import build_spend


class SpendSnapshotTest(unittest.TestCase):
    def test_pro_receipts_match_published_rows(self):
        site = ROOT / "data/site"
        usage = json.loads((site / "gpt-pro-spend-usage.json").read_text())
        identities = [row["id"] for row in usage["attempts"]]
        self.assertEqual(len(identities), len(set(identities)))
        addition = build_spend([site / "gpt-pro-spend-usage.json"], site / "prices.json")
        snapshot = json.loads((site / "spend.json").read_text())
        rows = {row["name"]: row for row in snapshot["models"]}
        self.assertEqual(addition["runs"], 14)
        self.assertEqual(addition["unknown_usage_runs"], 1)
        for row in addition["models"]:
            self.assertGreaterEqual(rows[row["name"]]["runs"], row["runs"])
            self.assertGreaterEqual(rows[row["name"]]["usd"], row["usd"])


if __name__ == "__main__":
    unittest.main()
