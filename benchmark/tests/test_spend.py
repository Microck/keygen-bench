"""Offline pricing and historical-usage accounting contracts."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


BUILDER = Path(__file__).resolve().parents[2] / "web/classic/build_spend.py"


class SpendTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def build(self, attempts, price):
        usage = self.root / "usage.json"
        prices = self.root / "prices.json"
        output = self.root / "spend.json"
        usage.write_text(json.dumps({"attempts": attempts}))
        prices.write_text(json.dumps({"models": [price]}))
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--input", str(usage), "--prices", str(prices), "--output", str(output)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(output.read_text())

    def price(self, **changes):
        return {"id": "example", "maker": "Example", "input_usd_per_m": 2,
                "cached_input_usd_per_m": 1, "output_usd_per_m": 4,
                "source_url": "https://developers.openai.com/api/docs/pricing", **changes}

    def test_context_boundary_and_cache_writes_are_priced_per_request(self):
        first = {"prompt_tokens": 199999, "cached_tokens": 99999,
                 "cache_write_tokens": 10000, "completion_tokens": 200}
        second = {"prompt_tokens": 200000, "cached_tokens": 100000,
                  "cache_write_tokens": 10000, "completion_tokens": 200}
        totals = {key: first[key] + second[key] for key in first}
        spend = self.build(
            [{"id": "campaign:one", "model": "example", "totals": totals, "requests": [first, second]}],
            self.price(cache_write_usd_per_m=2.5, tiers=[{
                "min_prompt_tokens": 200000, "input_usd_per_m": 4,
                "cached_input_usd_per_m": 2, "output_usd_per_m": 6, "cache_write_usd_per_m": 5,
            }]),
        )
        self.assertEqual(spend["total_usd"], 0.92)
        self.assertEqual(spend["models"][0]["usd"], 0.917)
        self.assertEqual((spend["priced_runs"], spend["unpriced_runs"]), (1, 0))

    def test_partial_usage_contributes_known_cost_but_stays_unpriced(self):
        recorded = {"prompt_tokens": 1000000, "cached_tokens": 0, "completion_tokens": 1000000}
        spend = self.build([
            {"id": "campaign:failed", "model": "example", "totals": recorded, "requests": [recorded, None]},
            {"id": "campaign:missing", "model": "unknown", "totals": None},
        ], self.price())
        self.assertEqual(spend["total_usd"], 6)
        self.assertEqual((spend["runs"], spend["priced_runs"], spend["unpriced_runs"]), (2, 0, 2))
        self.assertEqual((spend["partial_priced_runs"], spend["unknown_usage_runs"]), (1, 2))
        self.assertEqual(spend["unpriced_tokens"], {"input": 1000000, "output": 1000000})
        self.assertIsNone(next(model for model in spend["models"] if model["name"] == "unknown")["usd"])
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (6, 6))
        self.assertEqual((spend["bounded_runs"], spend["partial_bounded_runs"], spend["unknown_cost_runs"]), (0, 1, 2))

    def test_aggregate_usage_does_not_prove_the_long_context_tier(self):
        spend = self.build([{
            "id": "one", "model": "example",
            "totals": {"prompt_tokens": 300000, "cached_tokens": 0, "completion_tokens": 100},
        }], self.price(tiers=[{
            "min_prompt_tokens": 200000, "input_usd_per_m": 4,
            "cached_input_usd_per_m": 2, "output_usd_per_m": 6,
        }]))
        self.assertIsNone(spend["total_usd"])
        self.assertEqual((spend["priced_runs"], spend["unpriced_runs"]), (0, 1))
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (0.6004, 1.2006))
        self.assertEqual((spend["bounded_runs"], spend["unknown_cost_runs"]), (1, 0))

    def test_unknown_cache_write_rate_is_not_the_uncached_input_rate(self):
        spend = self.build([{
            "id": "one", "model": "example", "totals": {
                "prompt_tokens": 1000000, "cached_tokens": 0, "completion_tokens": 100,
                "cache_write_tokens": 500000,
            },
        }], self.price())
        self.assertIsNone(spend["total_usd"])
        self.assertEqual(spend["unpriced_runs"], 1)
        self.assertIsNone(spend["recorded_usage_cost_range_usd"])
        self.assertEqual(spend["unknown_cost_runs"], 1)

    def test_missing_cache_write_usage_is_not_assumed_zero(self):
        spend = self.build([{
            "id": "one", "model": "example",
            "totals": {"prompt_tokens": 1000000, "cached_tokens": 0, "completion_tokens": 100},
        }], self.price(cache_write_usd_per_m=2.5))
        self.assertIsNone(spend["total_usd"])
        self.assertEqual(spend["unpriced_runs"], 1)
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (2.0004, 2.5004))

    def test_untrusted_lookalike_source_cannot_publish_a_price(self):
        spend = self.build([{
            "id": "one", "model": "example",
            "totals": {"prompt_tokens": 1000000, "cached_tokens": 0, "completion_tokens": 100},
        }], self.price(source_url="https://developers.openai.com.example.invalid/pricing"))
        self.assertIsNone(spend["total_usd"])
        self.assertEqual(spend["unpriced_runs"], 1)

    def test_documented_free_model_is_not_missing_pricing(self):
        spend = self.build([{
            "id": "one", "model": "space-bunny-free",
            "totals": {"prompt_tokens": 1000000, "cached_tokens": 0, "completion_tokens": 100},
        }], self.price(id="space-bunny-free", source_url="https://opencode.ai/docs/go/",
                      input_usd_per_m=0, cached_input_usd_per_m=0, output_usd_per_m=0))
        self.assertEqual(spend["total_usd"], 0)
        self.assertEqual((spend["priced_runs"], spend["unpriced_runs"]), (1, 0))

    def test_duplicate_attempt_identity_across_inputs_is_rejected(self):
        record = {"id": "same", "model": "example", "totals": None}
        inputs = []
        for name in ("first", "second"):
            path = self.root / f"{name}.json"
            path.write_text(json.dumps({"attempts": [record]}))
            inputs.extend(["--input", str(path)])
        prices = self.root / "prices.json"
        prices.write_text(json.dumps({"models": [self.price()]}))
        output = self.root / "spend.json"
        result = subprocess.run(
            [sys.executable, str(BUILDER), *inputs, "--prices", str(prices), "--output", str(output)],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_exact_contribution_is_counted_once_beside_cache_duration_bounds(self):
        exact = {"prompt_tokens": 1000000, "cached_tokens": 500000, "completion_tokens": 1000000,
                 "cache_write_tokens": 0, "cache_write_1h_tokens": 0}
        uncertain = {"prompt_tokens": 1000000, "cached_tokens": 500000, "completion_tokens": 1000000,
                     "cache_write_tokens": 100000}
        spend = self.build([
            {"id": "exact", "model": "example", "totals": exact},
            {"id": "bounded", "model": "example", "totals": uncertain},
        ], self.price(cache_write_usd_per_m=2.5, cache_write_1h_usd_per_m=4))
        self.assertEqual(spend["total_usd"], 5.5)
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (11.05, 11.85))
        self.assertEqual((spend["priced_runs"], spend["bounded_runs"], spend["unknown_cost_runs"]), (1, 1, 0))

    def test_unknown_usage_is_not_zero_but_recorded_zero_is_priceable(self):
        spend = self.build([
            {"id": "missing", "model": "example", "totals": None},
            {"id": "zero", "model": "example",
             "totals": {"prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0}},
        ], self.price())
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (0, 0))
        self.assertEqual((spend["priced_runs"], spend["unknown_usage_runs"], spend["unknown_cost_runs"]), (1, 1, 1))

    def test_unreachable_tier_is_excluded_from_aggregate_bounds(self):
        spend = self.build([{
            "id": "short", "model": "example",
            "totals": {"prompt_tokens": 199999, "cached_tokens": 100000, "completion_tokens": 100},
        }], self.price(cache_write_usd_per_m=2.5, tiers=[{
            "min_prompt_tokens": 200000, "input_usd_per_m": 40,
            "cached_input_usd_per_m": 20, "output_usd_per_m": 60, "cache_write_usd_per_m": 50,
        }]))
        interval = spend["recorded_usage_cost_range_usd"]
        self.assertEqual((interval["min"], interval["max"]), (0.3003, 0.3504))


if __name__ == "__main__":
    unittest.main()
