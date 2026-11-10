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


    def test_o3_receipts_match_published_row(self):
        site = ROOT / "data/site"
        addition = build_spend([site / "o3-spend-usage.json"], site / "prices.json")
        snapshot = json.loads((site / "spend.json").read_text())
        row = next(row for row in snapshot["models"] if row["name"] == "o3")
        self.assertEqual(addition["models"], [row])
        self.assertEqual(addition["unknown_usage_runs"], 0)


    def test_gpt_5_receipts_match_published_row(self):
        site = ROOT / "data/site"
        addition = build_spend([site / "gpt-5-spend-usage.json"], site / "prices.json")
        snapshot = json.loads((site / "spend.json").read_text())
        row = next(row for row in snapshot["models"] if row["name"] == "gpt-5")
        self.assertEqual(addition["models"], [row])
        self.assertEqual(addition["unknown_usage_runs"], 0)


    def test_gpt_5_mini_receipts_match_published_row(self):
        site = ROOT / "data/site"
        addition = build_spend([site / "gpt-5-mini-spend-usage.json"], site / "prices.json")
        snapshot = json.loads((site / "spend.json").read_text())
        row = next(row for row in snapshot["models"] if row["name"] == "gpt-5-mini")
        self.assertEqual(addition["models"], [row])
        self.assertEqual(addition["unknown_usage_runs"], 0)


    def test_gpt_5_nano_receipts_match_published_row(self):
        site = ROOT / "data/site"
        addition = build_spend([site / "gpt-5-nano-spend-usage.json"], site / "prices.json")
        snapshot = json.loads((site / "spend.json").read_text())
        row = next(row for row in snapshot["models"] if row["name"] == "gpt-5-nano")
        self.assertEqual(addition["models"], [row])
        self.assertEqual(addition["unknown_usage_runs"], 0)


if __name__ == "__main__":
    unittest.main()
