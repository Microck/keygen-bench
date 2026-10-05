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

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from build import estimate_cost, estimate_cost_range, estimate_request_cost, price_id, public_maker, public_price


TOKEN_FIELDS = ("prompt_tokens", "cached_tokens", "completion_tokens",
                "cache_write_tokens", "cache_write_1h_tokens")
RATE_FIELDS = ("input_usd_per_m", "cached_input_usd_per_m", "output_usd_per_m",
               "cache_write_usd_per_m", "cache_write_1h_usd_per_m")


def validate_totals(totals: dict, identity: str) -> None:
    if not isinstance(totals, dict):
        raise ValueError(f"{identity}: totals must be an object or null")
    for field in TOKEN_FIELDS:
        value = totals.get(field, 0 if field in TOKEN_FIELDS[3:] else None)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{identity}: {field} must be a nonnegative integer; use totals: null for unknown usage")
    if sum(totals.get(field, 0) for field in ("cached_tokens", *TOKEN_FIELDS[3:])) > totals["prompt_tokens"]:
        raise ValueError(f"{identity}: cached and cache-write tokens cannot exceed prompt tokens")


def build_spend(inputs: list[Path], prices_path: Path) -> dict:
    prices = {}
    for price in json.loads(prices_path.read_text())["models"]:
        name = price_id(price["id"])
        if not name or name in prices:
            raise ValueError("Each price needs a nonempty model ID unique in the pricing table")
        prices[name] = price
        thresholds = set()
        for row in [price, *price.get("tiers", [])]:
            if row is not price:
                threshold = row.get("min_prompt_tokens")
                if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0 or threshold in thresholds:
                    raise ValueError(f"{name}: tier thresholds must be unique nonnegative integers")
                thresholds.add(threshold)
            for field in RATE_FIELDS:
                value = row.get(field)
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                          or not math.isfinite(value) or value < 0):
                    raise ValueError(f"{name}: {field} must be a nonnegative finite number or null")
            if (row.get("input_usd_per_m") is None) != (row.get("output_usd_per_m") is None):
                raise ValueError(f"{name}: input and output prices must both be known or both null")
    seen, models, costs, lower_bounds, upper_bounds = set(), {}, [], [], []
    priced_runs = partial_priced_runs = unknown_usage_runs = 0
    bounded_runs = partial_bounded_runs = unknown_cost_runs = 0
    unpriced_input = unpriced_output = 0
    for path in inputs:
        for record in json.loads(path.read_text())["attempts"]:
            identity = record["id"]
            if not isinstance(identity, str) or not identity.strip() or identity in seen:
                raise ValueError("Each attempt needs a nonempty ID unique across all inputs")
            seen.add(identity)
            name = price_id(record["model"])
            price = prices.get(name, {})
            safe_price = public_price(price)
            totals = record.get("totals")
            complete = record.get("usage_complete", totals is not None)
            if not isinstance(complete, bool):
                raise ValueError(f"{identity}: usage_complete must be a boolean")
            if totals is not None:
                validate_totals(totals, identity)
            if totals is None and complete:
                raise ValueError(f"{identity}: unknown totals cannot have complete usage")
            known_costs = []
            ranges = []
            unknown_cost = totals is None
            requests = record.get("requests")
            if requests is not None:
                if not isinstance(requests, list) or not requests:
                    raise ValueError(f"{identity}: requests must be a nonempty array of usage objects or null entries")
                observed = {field: 0 for field in TOKEN_FIELDS}
                for request in requests:
                    if request is None:
                        complete = False
                        continue
                    validate_totals(request, identity)
                    for field in TOKEN_FIELDS:
                        observed[field] += request.get(field, 0)
                    usd = estimate_request_cost(request, safe_price)
                    if usd is not None:
                        known_costs.append(usd)
                        ranges.append({"min": usd, "max": usd})
                    else:
                        interval = estimate_cost_range(request, safe_price, per_request=True)
                        if interval is not None:
                            ranges.append(interval)
                        else:
                            unknown_cost = True
                if totals is None or any(observed[field] != totals.get(field, 0) for field in TOKEN_FIELDS):
                    raise ValueError(f"{identity}: totals must equal the recorded request usage")
                fully_priced = complete and len(known_costs) == len(requests)
            else:
                # Aggregate usage cannot establish each request's long-context tier.
                tier_unknown = totals is not None and any(
                    totals["prompt_tokens"] >= tier["min_prompt_tokens"] for tier in safe_price.get("tiers", []))
                usd = estimate_cost(totals, safe_price, round_digits=None) if totals is not None and not tier_unknown else None
                if usd is not None:
                    known_costs.append(usd)
                    ranges.append({"min": usd, "max": usd})
                else:
                    interval = estimate_cost_range(totals, safe_price) if totals is not None else None
                    if interval is not None:
                        ranges.append(interval)
                    else:
                        unknown_cost = True
                fully_priced = complete and usd is not None
            unknown_usage_runs += not complete
            fully_bounded = complete and not unknown_cost
            bounded = fully_bounded and not fully_priced
            partial_bounded = not fully_bounded and bool(ranges)
            bounded_runs += bounded
            partial_bounded_runs += partial_bounded
            unknown_cost_runs += not fully_bounded
            model = models.setdefault(name, {"name": name, "maker": public_maker(name, price),
                                             "runs": 0, "usd": None, "unpriced_runs": 0,
                                             "bounded_runs": 0, "partial_bounded_runs": 0, "unknown_cost_runs": 0})
            model["runs"] += 1
            model["bounded_runs"] += bounded
            model["partial_bounded_runs"] += partial_bounded
            model["unknown_cost_runs"] += not fully_bounded
            if ranges:
                lower = math.fsum(value["min"] for value in ranges)
                upper = math.fsum(value["max"] for value in ranges)
                lower_bounds.append(lower)
                upper_bounds.append(upper)
                model.setdefault("_lower", []).append(lower)
                model.setdefault("_upper", []).append(upper)
            if fully_priced:
                priced_runs += 1
            else:
                model["unpriced_runs"] += 1
                unpriced_input += (totals or {}).get("prompt_tokens", 0)
                unpriced_output += (totals or {}).get("completion_tokens", 0)
                partial_priced_runs += bool(known_costs)
            if known_costs:
                costs.extend(known_costs)
                model.setdefault("_costs", []).extend(known_costs)
    for model in models.values():
        model_costs = model.pop("_costs", [])
        model["usd"] = round(math.fsum(model_costs), 4) if model_costs else None
        model["recorded_usage_cost_range_usd"] = recorded_range(model.pop("_lower", []), model.pop("_upper", []))
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "basis": "Only explicitly supplied, deduplicated started attempts. Recorded token usage at documented maker list prices; not a provider bill. total_usd includes only priceable recorded portions. The recorded-usage interval also covers documented context tiers and missing cache-write splits. Missing usage and undocumented prices have no finite upper bound here. Neither total describes complete historical spending.",
        "total_usd": round(math.fsum(costs), 2) if costs else None,
        "runs": len(seen), "priced_runs": priced_runs, "unpriced_runs": len(seen) - priced_runs,
        "partial_priced_runs": partial_priced_runs, "unknown_usage_runs": unknown_usage_runs,
        "bounded_runs": bounded_runs, "partial_bounded_runs": partial_bounded_runs, "unknown_cost_runs": unknown_cost_runs,
        "recorded_usage_cost_range_usd": recorded_range(lower_bounds, upper_bounds),
        "unpriced_tokens": {"input": unpriced_input, "output": unpriced_output},
        "models": sorted(models.values(), key=lambda model: (model["usd"] is None, -(model["usd"] or 0), model["name"])),
    }


def recorded_range(lower: list[float], upper: list[float]) -> dict | None:
    if not lower:
        return None
    unit = Decimal("0.0001")
    return {
        "min": float(Decimal(str(math.fsum(lower))).quantize(unit, rounding=ROUND_FLOOR)),
        "max": float(Decimal(str(math.fsum(upper))).quantize(unit, rounding=ROUND_CEILING)),
        "reason": "Recorded, priceable usage only, including known portions of incomplete attempts and documented pricing bounds. Missing usage or prices are excluded. This is not an upper bound on historical spending or a provider bill.",
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
