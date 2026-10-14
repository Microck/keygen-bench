"""Compare a repository publication with reviewed live and listener-preview data.

Score/rank changes against the craft-era live data are expected. Listener best
scores, XM identities, public slugs and published model membership must agree.
Other field differences are listed rather than silently discarded.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def compare(publication: dict, live: dict, preview: dict) -> dict:
    def by_xm(data):
        return {row["provenance"]["input_sha256"]["submission/tune.xm"]: row for row in data["runs"]}

    current, old = by_xm(publication), by_xm(live)
    failures = []
    if set(current) != set(old):
        failures.append({"field": "attempts", "missing": sorted(set(old)-set(current)), "added": sorted(set(current)-set(old))})
    current_models = {row["model_key"] for row in current.values()}
    old_models = {row["model_key"] for row in old.values()}
    if current_models != old_models:
        failures.append({"field": "models", "missing": sorted(old_models-current_models), "added": sorted(current_models-old_models)})
    differences = []
    fields = ("slug", "name", "label", "model_key", "maker", "usage", "price", "cost_usd", "cost_lower_bound",
              "cost_range_usd", "cohort", "tier", "flags", "module", "audio", "loop")
    for key in sorted(current.keys() & old.keys()):
        row, previous = current[key], old[key]
        for field in fields:
            if row.get(field) != previous.get(field):
                item = {"slug": row["slug"], "field": field, "before": previous.get(field), "after": row.get(field)}
                (failures if field == "slug" else differences).append(item)
        for field in ("campaign_id", "campaign_sha256", "cohort_fingerprint", "condition_fingerprint",
                      "source_campaign_id", "repetition_campaign_sha256"):
            if row["provenance"].get(field) != previous["provenance"].get(field):
                differences.append({"slug": row["slug"], "field": "provenance." + field,
                    "before": previous["provenance"].get(field), "after": row["provenance"].get(field)})
        for field in ("xm", "audio", "wav"):
            if not row.get("media", {}).get(field):
                failures.append({"slug": row["slug"], "field": "media." + field})
            elif Path(row["media"][field]).name != Path(previous["media"][field]).name:
                failures.append({"slug": row["slug"], "field": "media.filename." + field})
    def best(data):
        result = {}
        for row in data["runs"]:
            if row.get("score") is not None:
                result[row["model_key"]] = max(row["score"], result.get(row["model_key"], float("-inf")))
        return result
    actual_best, expected_best = best(publication), best(preview)
    for model in sorted(actual_best.keys() | expected_best.keys()):
        if actual_best.get(model) != expected_best.get(model):
            failures.append({"model": model, "field": "listener_best_score", "before": expected_best.get(model), "after": actual_best.get(model)})
    old_groups = {group["model_key"]: group for group in live.get("repetition_groups", [])}
    for group in publication.get("repetition_groups", []):
        previous = old_groups.get(group["model_key"], {})
        for field in ("name", "maker", "tier", "cohort_key", "declared", "eligible", "pending", "state",
                      "campaign_id", "campaign_ids", "condition_fingerprint", "outside_condition", "reruns"):
            if group.get(field) != previous.get(field):
                differences.append({"model": group["model_key"], "field": "group." + field,
                    "before": previous.get(field), "after": group.get(field)})
    return {"attempts": len(current), "models": len(current_models), "shared_attempts": len(current.keys() & old.keys()),
            "failures": failures, "difference_counts": dict(Counter(item["field"] for item in differences)),
            "history_counts": {"groups_before": len(live.get("repetition_groups", [])),
                               "groups_after": len(publication.get("repetition_groups", [])),
                               "campaigns_before": len(live.get("campaigns", [])),
                               "campaigns_after": len(publication.get("campaigns", []))},
            "differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--listener-preview", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Write the complete machine-readable differences")
    args = parser.parse_args()
    result = compare(*(json.loads(path.read_text()) for path in (args.data, args.live, args.listener_preview)))
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "differences"}, indent=2))
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
