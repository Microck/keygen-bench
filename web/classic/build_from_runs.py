"""Build a publication from the repository's predetermined attempt slots.

Maintainer slots are runs/<model>/attempt-1..3. Reviewed community publications
are runs/<model>/community/<YYYY-MM-DD>-<handle>/attempt-1..3, beside the
maintainer slots and never in them. No campaign discovery, provider calls or
private server paths are used. --no-media runs the same integrity checks and
builds metadata/cards without media derivatives; it is useful for pull-request
validation, but its output is not deployable.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "benchmark"), str(HERE)]
from benchmark.report import (MAX_TIER_PREFIX, attempt_row, campaign_cohort, condition_fingerprint, counts, digest,
                              read_cohort, tier_label)
from build import FLAG_RULES, copy_frontend, estimate_cost, price_id, public_maker, public_price, slug
from collect_public import public_run, sha256, verified_media, write_json

SITE = ROOT / "data/site"


def read_json(path: Path):
    return json.loads(path.read_text())


def display_name(name: str) -> str:
    name = re.sub(r"^[A-Za-z0-9._-]+/", "", name.lower())
    name = re.sub(r"(muse-spark-[a-z0-9.-]+?)-contributor\b", r"\1", name)
    return re.sub(r"-free(?=$| )", "", name.replace(":free", ""))


def checked_path(directory: Path, relative: str) -> Path:
    path = directory / relative
    if (Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink()
            or not path.is_file() or not path.resolve().is_relative_to(directory.resolve())):
        raise ValueError(f"{directory}: invalid or missing artifact {relative}")
    return path


def load_attempt(directory: Path, report_root: Path, bundles: dict | None = None,
                 community: str | None = None) -> tuple[dict, dict, str]:
    """Load one slot. `community` is the submission directory name for community slots, else None."""
    identity = read_json(checked_path(directory, "ATTEMPT.json"))
    publication = identity.get("publication")
    if bool(publication) != bool(community):
        raise ValueError(f"{directory}: community receipts belong only under runs/<model>/community/<submission>/")
    attempt_id = identity["attempt_id"]
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", attempt_id):
        raise ValueError(f"{directory}: invalid attempt identity")
    status = read_json(checked_path(directory, "status.json"))
    if status.get("attempt_id") != attempt_id or identity["slot"] != directory.name:
        raise ValueError(f"{directory}: organizer identity mismatch")
    link = report_root / attempt_id
    if (directory / "campaign.json").exists():
        config, campaign_hash, fingerprint = read_cohort(checked_path(directory, "campaign.json"))
        link.symlink_to(directory.resolve(), target_is_directory=True)
    else:
        # Standalone contribution runs seal their configuration in spec.json, not
        # campaign.json. Adapt that retained format for the same report checks.
        spec = read_json(checked_path(directory, "spec.json"))
        if spec["model"] != status["model"]:
            raise ValueError(f"{directory}: standalone model differs from sealed spec")
        config = {**spec["config"], "models": [spec["model"]],
                  "schema": "keygen-native-campaign-3",
                  "campaign_id": identity["campaign_id"] if publication else
                  "next-max-tier-" + identity["campaign_id"]}
        campaign_hash, fingerprint = digest(config), digest(config)
        link.mkdir()
        for filename in ("status.json", "profile.json"):
            (link / filename).symlink_to(checked_path(directory, filename))
        (link / "campaign.json").write_text(json.dumps({"campaign": config, "sha256": campaign_hash}))
    try:
        row = attempt_row(report_root, attempt_id, None, fingerprint or campaign_hash,
                          campaign_hash, campaign_cohort(config))
    finally:
        if link.is_symlink():
            link.unlink()
        else:
            shutil.rmtree(link)
    if row["error"] and status.get("status") == "RENDERED_UNSCORED":
        raise ValueError(f"{directory}: {row['error']}")
    if not publication and not config["campaign_id"].startswith(MAX_TIER_PREFIX):
        # The organizer places only highest-declared-tier maintainer runs in attempt slots,
        # as the standalone adapter above already assumes. A campaign named without the
        # prefix keeps its sealed file; only its publication condition label is derived here.
        row["cohort"] = campaign_cohort({**config, "campaign_id": MAX_TIER_PREFIX + config["campaign_id"]})
        row["tier"] = tier_label(status["model"], row["cohort"]["condition"])
    row["source_campaign_sha256"] = campaign_hash
    row["source_campaign_id"] = f"campaign-{campaign_hash}"
    row["condition_fingerprint"] = condition_fingerprint(config, status["model"])
    row["repetition"] = int(directory.name.removeprefix("attempt-"))
    if publication:
        bundle = (bundles or {}).get(publication["bundle_sha256"])
        if (not bundle or bundle.name != community or publication["kind"] != "community-submitted"
                or not publication.get("note")):
            raise ValueError(f"{directory}: missing reviewed community bundle or disclosure")
        manifest = read_json(bundle / "manifest.json")
        frozen = manifest["environment"]["contract"]
        if (config["prompts"] != frozen["prompt"] or config["limits"] != frozen["limits"]
                or config["native"] != frozen["native"] or config["models"] != [manifest["environment"]["model"]]
                or config["image"] != manifest["environment"]["images"]["agent"]
                or config["visualizer_image"] != manifest["environment"]["images"]["visualizer"]):
            raise ValueError(f"{directory}: reviewed contract mismatch")
        source = bundle / directory.name
        submitted = read_json(source / "status.json")
        if any(status.get(key) != submitted.get(key) for key in
               ("model", "attempt_id", "repetition", "started_at", "finished_at", "wall_seconds", "totals")):
            raise ValueError(f"{directory}: reviewed submission identity mismatch")
        for retained, original in (("submission/tune.xm", "tune.xm"),
                                   ("trajectory.json", "trajectory.json"),
                                   ("transport.jsonl", "transport.jsonl")):
            if (source / original).is_file() and sha256(checked_path(directory, retained)) != sha256(source / original):
                raise ValueError(f"{directory}: reviewed submission checksum mismatch: {retained}")
        row["publication"] = publication
        row["cohort"] = {"key": "community/" + publication["bundle_sha256"],
                         "condition": "community-submitted", "prompt_version": config["prompts"]["version"],
                         "label": "Community-submitted, maintainer re-scored; not comparatively ranked"}
    return row, config, campaign_hash


def scored_profile(row: dict, directory: Path, evidence: dict, stage: Path) -> tuple[dict, dict]:
    profile_path = checked_path(directory, "profile.json")
    if sha256(profile_path) != row["retained_profile_sha256"]:
        raise ValueError(f"{directory}: retained profile changed during publication")
    profile = read_json(profile_path)
    for relative, expected in profile["inputs"]["artifacts"].items():
        if relative == "status.json":
            # report.attempt_row already verifies the evaluated status, including
            # hash-proven recovery of post-evaluation finalization failures.
            expected = row["retained_status_sha256"]
        if relative not in {"submission/tune.xm", "canonical/canonical.wav"}:
            if sha256(checked_path(directory, relative)) != expected:
                raise ValueError(f"{directory}: pinned artifact checksum mismatch: {relative}")
    verification = verified_media(directory, profile, stage)
    xm_hash = verification["input_sha256"]["submission/tune.xm"]
    wav_hash = verification["input_sha256"]["canonical/canonical.wav"]
    from benchmark.score import artifact_caps, benchmark_score, flags, listen
    entry = evidence.get(xm_hash)
    if entry:
        if entry["canonical_wav_sha256"] != wav_hash:
            raise ValueError(f"{directory}: listener evidence canonical WAV mismatch")
        craft = copy.deepcopy(entry["craft"])
        if craft.get("caps") != artifact_caps(profile["structure"], profile["audio"]):
            raise ValueError(f"{directory}: listener evidence artifact caps mismatch")
        uncapped = round(10 * craft["listener"]["content_enjoyment"], 1)
        score = min([uncapped] + [cap["ceiling"] for cap in craft["caps"]])
        if (not math.isfinite(score) or craft["uncapped"] != uncapped
                or craft["craft_score"] != score or entry["new_score"] != score):
            raise ValueError(f"{directory}: inconsistent listener score evidence")
        profile["audio"]["spectral"] = entry["spectral"]
        profile["flags"] = flags(profile["structure"], profile["audio"], profile["process"],
                                 profile["mix"], profile["loop"])
    else:
        craft = benchmark_score(profile["structure"], profile["audio"], profile["loop"],
                                listen(stage / "canonical.wav"))
    profile.update(score_version="listener-v1", craft=craft)
    return profile, verification


def build_from_runs(runs_root: Path, output: Path, listener_scores: Path,
                    *, no_media: bool = False, models: list[str] | None = None,
                    site: Path = SITE, cards: bool = True, submissions: Path = ROOT / "submissions") -> dict:
    started = time.monotonic()
    runs_root, output = runs_root.resolve(), output.resolve()
    if (output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(runs_root)
            or runs_root.is_relative_to(output)):
        raise ValueError("Publication must be separate from source inputs")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Publication output must be new or empty")
    metadata = read_json(site / "model-metadata.json")
    prices = {entry["id"]: entry for entry in read_json(site / "prices.json")["models"]}
    identities = read_json(site / "published-identities.json")
    exclusions = read_json(site / "publication-policy.json")["excluded_models"]
    scores = read_json(listener_scores)
    evidence_sha256 = sha256(listener_scores)
    if scores.get("score_version") != "listener-v1":
        raise ValueError("Listener evidence must use listener-v1")
    evidence = {}
    for entry in scores["attempts"]:
        if entry.get("eligible"):
            key = entry["xm_sha256"]
            if key in evidence and evidence[key] != entry:
                raise ValueError(f"Conflicting listener evidence for {key}")
            evidence[key] = entry
    selected = sorted(path for path in runs_root.iterdir() if path.is_dir()
                      and not path.is_symlink() and (not models or path.name in models))
    if models and set(models) != {path.name for path in selected}:
        raise ValueError("Requested model directories are missing")
    selected = [path for path in selected if path.name not in exclusions]
    # Maintainer slots and each reviewed community submission are separate attempt sets of a model.
    sets = []
    for model in selected:
        sets.append((model.name, None, sorted(model.glob("attempt-*"))))
        community = model / "community"
        if community.is_symlink() or (community.exists() and not community.is_dir()):
            raise ValueError(f"{community}: invalid community directory")
        for source in sorted(community.iterdir()) if community.is_dir() else []:
            if source.is_symlink() or not source.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[A-Za-z0-9-]+", source.name):
                raise ValueError(f"{source}: community publications are <YYYY-MM-DD>-<handle> directories")
            sets.append((f"{model.name}/community/{source.name}", source.name, sorted(source.glob("attempt-*"))))
    # Validate only referenced bundles, once each. Unreviewed submissions are not publication inputs.
    from benchmark.contrib.validate_bundle import validate
    required = set()
    for _, community, directories in sets:
        for directory in directories if community else []:
            publication = read_json(checked_path(directory, "ATTEMPT.json")).get("publication")
            if publication:
                required.add(publication["bundle_sha256"])
    bundles = {}
    for manifest in submissions.glob("*/*/manifest.json") if required else []:
        manifest_hash = sha256(manifest)
        if manifest_hash in required:
            validate(manifest.parent)
            bundles[manifest_hash] = manifest.parent
    if required - bundles.keys():
        raise ValueError("Missing reviewed community bundle")
    loaded, missing = [], []
    with tempfile.TemporaryDirectory(prefix="keygen-site-") as temporary:
        work = Path(temporary)
        report_root = work / "report"
        report_root.mkdir()
        for set_id, community, directories in sets:
            for directory in directories:
                if directory.is_symlink() or not directory.is_dir() or not re.fullmatch(r"attempt-[123]", directory.name):
                    raise ValueError(f"{directory}: invalid ranked slot")
                row, config, campaign_hash = load_attempt(directory, report_root, bundles, community)
                row["retained_profile_sha256"] = sha256(directory / "profile.json") if (directory / "profile.json").is_file() else None
                row["retained_status_sha256"] = sha256(directory / "status.json")
                row.pop("profile", None)
                selection = config.get("policies", {}).get("attempt_selection")
                loaded.append((set_id, community, directory, row, selection, campaign_hash))
                if row["eligible"]:
                    xm_hash = sha256(checked_path(directory, "submission/tune.xm"))
                    if xm_hash not in evidence:
                        missing.append(f"{set_id}/{directory.name}")
        if missing and not os.environ.get("KEYGEN_LISTENER_PYTHON"):
            raise ValueError("Missing listener-v1 evidence; set KEYGEN_LISTENER_PYTHON to rate: " + ", ".join(missing))
        if not any(row["eligible"] for _, _, _, row, _, _ in loaded):
            raise ValueError("No eligible ranked attempts")
        output.mkdir(parents=True, exist_ok=True)
        dist = output / "dist"
        dist.mkdir()
        published, groups, campaign_rows = [], {}, {}
        for set_id, community, directory, row, selection, campaign_hash in loaded:
            ordinal = row["repetition"]
            cohort = row["cohort"]
            key = display_name(price_id(row["model"]))
            # The public key is the model route (/tracker/<key>); a community set gets its own.
            public_key = f"{key}-community-{community.lower()}" if community else key
            model = set_id.split("/", 1)[0]
            group = groups.setdefault(set_id, {"cohort_key": cohort["key"], "model_key": public_key,
                "name": display_name(model) + " (max-tier)", "tier": row["tier"],
                "maker": public_maker(display_name(model), {}),
                "campaign_id": f"campaign-{campaign_hash}", "campaign_sha256": campaign_hash,
                "condition_fingerprint": row["condition_fingerprint"],
                "declared": 3, "attempts": [], "ranking_policy": "best of 3", "outside_condition": []})
            if group["cohort_key"] != cohort["key"]:
                raise ValueError(f"{set_id}: ranked slots cross cohorts")
            if group["model_key"] != public_key:
                raise ValueError(f"{set_id}: ranked slots mix model identities")
            summary = {"ordinal": ordinal, "status": row["status"], "outcome": row["outcome"],
                "eligible": row["eligible"], "attempted": row["attempted"], "failure_category": row["failure_category"],
                "model_failure": row["model_failure"], "source_campaign_sha256": campaign_hash,
                "source_campaign_id": f"campaign-{campaign_hash}", "source": "ranked attempt slot",
                "stopped_by": None, "slug": None, "score": None, "ranked": False, "superseded": []}
            group["attempts"].append(summary)
            campaign_rows.setdefault(campaign_hash, []).append(row)
            if not row["eligible"]:
                continue
            stage = work / "inputs"
            profile, verification = scored_profile(row, directory, evidence, stage)
            xm_hash = verification["input_sha256"]["submission/tune.xm"]
            identity = identities.get(xm_hash, {})
            if identity and (identity["attempt_ordinal"] != ordinal or identity["model_key"] != public_key):
                identity = {}
            if key not in metadata:
                raise ValueError(f"Unknown model metadata: {key}")
            release = metadata[key].get("release_date")
            unknown_release = ("release_date" in metadata[key] and release is None
                               and bool(metadata[key].get("release_date_note")))
            if not unknown_release and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", release or ""):
                raise ValueError(f"Missing release_date: {key}")
            run_slug = identity.get("slug", f"{slug(public_key)}-a{ordinal}-{xm_hash[:12]}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", run_slug):
                raise ValueError(f"Invalid public slug: {run_slug}")
            source_evaluation = {key: row[key] for key in ("score_version", "evaluation_fingerprint")}
            source_evaluation["profile_sha256"] = row["retained_profile_sha256"]
            if xm_hash in evidence:
                listener_identity = evidence[xm_hash].get("listener", scores.get("listener"))
            else:
                from benchmark.score import listener_identity as local_listener_identity
                listener_identity = local_listener_identity()
            row["evaluation_fingerprint"] = digest({"score_version": "listener-v1",
                "input_sha256": verification["input_sha256"], "listener": listener_identity,
                "evidence_sha256": evidence_sha256 if xm_hash in evidence else None})
            row.update(profile=profile, score_version="listener-v1", craft=profile["craft"]["craft_score"])
            # The collector verifies the same inputs. Move its verified stage rather than decode twice.
            collector_stage = dist / ".verified" / run_slug
            collector_stage.parent.mkdir(exist_ok=True)
            shutil.move(stage, collector_stage)
            run = public_run(row, {"attempted_count": sum(r["attempted"] for s, _, _, r, _, _ in loaded if s == set_id)},
                             directory, dist, {"campaign_sha256": campaign_hash,
                             "attempt_selection": selection},
                             "repetitions", {price_id(row["model"]): prices.get(key, {})}, run_slug=run_slug,
                             no_media=no_media, verification=verification, lossless="flac")
            default_name = f"{key} community {community} (attempt {ordinal})" if community else f"{key} (max-tier, attempt {ordinal})"
            # Community routes differ from the model key, so carry the model's release date on the run.
            run.update(model_key=public_key, name=identity.get("name", default_name), ranked=False, release_date=release)
            run["provenance"].update(selected_by="best eligible score among three predetermined ordinals; ties use the lowest ordinal",
                evaluation_kind="listener-evidence" if xm_hash in evidence else "listener-local",
                listener=listener_identity, source_evaluation=source_evaluation,
                configuration_source="campaign.json" if (directory / "campaign.json").is_file() else "sealed standalone spec.json")
            if row.get("publication"):
                run.update(exhibition=True, publication_note=row["publication"]["note"])
                run["provenance"].update(row["publication"])
                run["provenance"]["configuration_source"] = "sealed community bundle contract"
            run["provenance"].pop("profile_sha256")
            # Known partial usage is a lower bound, not a zero bill.
            if run["cost_usd"] is None and row["usage_unknown"]:
                lower = estimate_cost(row["totals"], public_price(prices.get(key, {})))
                if lower is not None:
                    run.update(cost_usd=lower, cost_lower_bound=True)
            summary.update(slug=run_slug, score=run["score"])
            group_name = re.sub(r", attempt \d+\)$", ")", run["name"])
            group_name = re.sub(r" \(attempt \d+\)$", "", group_name)
            group.update(model_key=public_key, name=group_name, maker=run["maker"])
            published.append(run)
            shutil.rmtree(collector_stage)
            row.pop("profile")
            del profile
        by_slug = {run["slug"]: run for run in published}
        if len(by_slug) != len(published):
            raise ValueError("Duplicate public slugs")
        ranked = []
        for group in groups.values():
            attempts = group["attempts"]
            for ordinal in range(1, 4):
                if not any(a["ordinal"] == ordinal for a in attempts):
                    attempts.append({"ordinal": ordinal, "eligible": False, "attempted": False,
                                     "status": "RESERVED", "outcome": "UNATTEMPTED", "score": None, "slug": None, "ranked": False})
            attempts.sort(key=lambda a: a["ordinal"])
            eligible = [a for a in attempts if a["eligible"]]
            pending = sum(a["status"] in {"RESERVED", "MISSING", "RUNNING"} for a in attempts)
            state = ("complete" if len(eligible) == 3 else "pending" if not eligible or pending
                     else "complete_with_failures")
            group.update(eligible=len(eligible), eligible_attempts=len(eligible), pending=pending,
                         state=state, ranked_slug=None, best_ordinal=None)
            if eligible:
                best = min(eligible, key=lambda a: (-a["score"], a["ordinal"]))
                comparative = not by_slug[best["slug"]]["exhibition"]
                best["ranked"] = comparative
                group.update(ranked_slug=best["slug"], best_ordinal=best["ordinal"])
                for attempt in eligible:
                    run = by_slug[attempt["slug"]]
                    run.update(ranked=comparative and attempt is best, attempt_of=None if attempt is best else best["slug"])
                if comparative:
                    ranked.append(by_slug[best["slug"]])
        for cohort_key in {run["cohort"]["key"] for run in ranked}:
            members = sorted((run for run in ranked if run["cohort"]["key"] == cohort_key),
                             key=lambda run: (-run["score"], run["name"]))
            for index, run in enumerate(members, 1):
                run["rank"] = index
        cohorts = list({r["cohort"]["key"]: dict(r["cohort"]) for r in published}.values())
        for cohort in cohorts:
            cohort["results"] = sum(g["cohort_key"] == cohort["key"] and bool(g["ranked_slug"]) for g in groups.values())
            cohort["main_model_roster"] = sum(g["cohort_key"] == cohort["key"] for g in groups.values())
        generated = datetime.now(timezone.utc).isoformat()
        data = {"generated": generated, "dataset_kind": "native-best-of-three", "ranking_policy": "best of 3",
            "publication_note": f"Repository ranked slots {generated[:10]}", "ranked_results": len(ranked),
            "eligible_attempts": len(published), "pending_models": sum(not g["ranked_slug"] for g in groups.values()),
            "selection_counts": {"main_model_roster": len(groups)}, "cohorts": cohorts,
            "limitations": ["Ranking uses the best eligible score among three predetermined ordinals; ties use the lowest ordinal.",
                "Scores are 10 x Meta Audiobox Aesthetics content enjoyment, capped for silent or baked-sample artifacts.",
                "Only runs/<model>/attempt-1 through attempt-3 are published. Other attempts and private rerun histories are not read.",
                "MP3 is a listening derivative; FLAC is the retained continuous loop source; XM is the original submission.",
                "Costs are list-price estimates from recorded usage, not provider bills."],
            "campaigns": [{"campaign_id": f"campaign-{digest}", "campaign_sha256": digest,
                "scope": "repetitions", "generated": generated, "counts": counts(rows), "roster": []}
                for digest, rows in sorted(campaign_rows.items())], "flag_rules": FLAG_RULES,
            "runs": sorted(published, key=lambda r: r["name"]), "repetition_groups": list(groups.values()),
            "evaluation_provenance": {"score_version": "listener-v1", "listener": scores.get("listener"),
                "evidence_sha256": sha256(listener_scores)}, "media_omitted": no_media,
            "excluded_models": [{"model_key": name, "name": name, "reason": reason}
                                for name, reason in exclusions.items()]}
        write_json(dist / "data.json", data)
        for run in published:
            write_json(dist / "evaluations" / f"{run['slug']}.json",
                       {k: v for k, v in run.items() if k not in {"trace", "media", "price", "cost_usd", "cost_range_usd"}})
        for name in ["spend.json", "model-metadata.json"]:
            shutil.copyfile(site / name, dist / name)
        shutil.rmtree(dist / ".verified")
        copy_frontend(output)
        if cards:
            subprocess.run([sys.executable, str(HERE / "build_og.py"), "--dist", str(dist)], check=True)
    size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    print(f"{len(published)} eligible attempts, {len(ranked)} ranked models; {time.monotonic()-started:.1f}s; {size} bytes")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--listener-scores", type=Path, default=ROOT / "data/listener-v1-runs.json")
    parser.add_argument("--no-media", action="store_true")
    parser.add_argument("--model", action="append", help="Build only named model directories for local validation")
    args = parser.parse_args()
    build_from_runs(args.runs, args.out, args.listener_scores, no_media=args.no_media, models=args.model)


if __name__ == "__main__":
    main()
