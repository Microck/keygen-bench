"""Build a public spend summary from explicit local attempt-usage JSON and prices.

No hosts, directories or accounts are searched. Input IDs distinguish attempts,
including failed and retried attempts; IDs and paths never enter the output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from build import estimate_cost, price_id, public_maker, public_price


def build_spend(inputs: list[Path], prices_path: Path) -> dict:
    prices = {price_id(row["id"]): row for row in json.loads(prices_path.read_text())["models"]}
    for price in prices.values():
        for field in ("input_usd_per_m", "cached_input_usd_per_m", "output_usd_per_m"):
            value = price.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not math.isfinite(value) or value < 0):
                raise ValueError(f"{price['id']}: {field} must be a nonnegative finite number or null")
        if (price.get("input_usd_per_m") is None) != (price.get("output_usd_per_m") is None):
            raise ValueError(f"{price['id']}: input and output prices must both be known or both null")
    seen, models, costs = set(), {}, []
    unpriced_input = unpriced_output = 0
    for path in inputs:
        for record in json.loads(path.read_text())["attempts"]:
            identity = record["id"]
            if not isinstance(identity, str) or not identity.strip() or identity in seen:
                raise ValueError("Each attempt needs a nonempty ID unique across all inputs")
            seen.add(identity)
            name = price_id(record["model"])
            price = prices.get(name, {})
            totals = record.get("totals")
            if totals is not None:
                for field in ("prompt_tokens", "cached_tokens", "completion_tokens"):
                    value = totals.get(field)
                    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        raise ValueError(f"{identity}: {field} must be a nonnegative integer; use totals: null for unknown usage")
                if totals["cached_tokens"] > totals["prompt_tokens"]:
                    raise ValueError(f"{identity}: cached tokens cannot exceed prompt tokens")
            usd = estimate_cost(totals, public_price(price)) if totals is not None else None
            model = models.setdefault(name, {"name": name, "maker": public_maker(name, price),
                                             "runs": 0, "usd": None, "unpriced_runs": 0})
            model["runs"] += 1
            if usd is None:
                model["unpriced_runs"] += 1
                unpriced_input += (totals or {}).get("prompt_tokens", 0)
                unpriced_output += (totals or {}).get("completion_tokens", 0)
            else:
                costs.append(usd)
                model["usd"] = round((model["usd"] or 0) + usd, 4)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "basis": "Only the attempts supplied to build_spend.py. Token usage times the supplied maker list prices; not an actual provider bill. Unknown usage or prices are not counted as zero cost.",
        "total_usd": round(sum(costs), 2) if costs else None,
        "runs": len(seen), "priced_runs": len(costs), "unpriced_runs": len(seen) - len(costs),
        "unpriced_tokens": {"input": unpriced_input, "output": unpriced_output},
        "models": sorted(models.values(), key=lambda model: (model["usd"] is None, -(model["usd"] or 0), model["name"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, help="Local JSON with an attempts array; repeat to combine inputs")
    parser.add_argument("--prices", type=Path, required=True, help="Local JSON with a models array of maker prices")
    parser.add_argument("--output", type=Path, required=True, help="Write the summary here, normally <publication>/dist/spend.json")
    args = parser.parse_args()
    spend = build_spend(args.input, args.prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spend, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {spend['runs']} attempts ({spend['unpriced_runs']} unpriced) to {args.output}")


if __name__ == "__main__":
    main()
