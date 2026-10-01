"""Publish one explicit cohort from retained metadata, without rescoring or archive restore."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import quote
import uuid

if __package__:
    from .report_page import PAGE
else:
    from report_page import PAGE

SCHEMA = "keygen-cohort-report-2"
ATTEMPT_SELECTION = "first_success_up_to_three_attempts"
# Quota, funds and rate-limit (429) failures are provider limits, never model or musical failures;
# so is a request the provider content filter blocked on every allowed send (CONTENT_FILTER).
NON_MODEL_FAILURES = {"INFRA", "AUTH", "QUOTA", "CONTENT_FILTER", "TRANSPORT", "PROTOCOL", "EVAL"}
PENDING_STATUSES = {"MISSING", "RESERVED", "RUNNING"}
SCORE_ROLE = "Auxiliary tonal-development diagnostic, not a musical-quality ranking."
ROUTE_KEYS = ("provider", "api", "base_url", "response_model")
DEFAULT_PROMPT_VERSION = "prompt-v1"  # frozen campaigns compiled before prompts carried a version
MAX_TIER_PREFIX = "next-max-tier-"
TIER_NOTE = ("'Highest declared tier' means the highest documented reasoning control on that exact route "
             "(for example max, xhigh, high, thinking-on or none-available), not equal compute: levels are "
             "vendor-specific and not comparable across providers. 'Provider default effort' means no reasoning "
             "control was sent. Each cohort is published in its own table and never ranked with another cohort.")
SAMPLE_NOTE = ("Each published score is one quality sample: the first valid attempt among up to three sequential "
               "attempts. Later attempts are not run after it, so no median, range or variance exists. Validity "
               "and attempts-to-valid are shown next to each score; quota, funds, rate-limit and auth stops are "
               "infrastructure, and the slots they leave reserved stay pending, not failed.")
UNIDENTIFIED_COHORT = {"key": "unidentified", "condition": "unidentified", "prompt_version": None,
                       "label": "unidentified cohort (no readable frozen campaign)"}


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def read_cohort(path: Path) -> tuple[dict, str, str | None]:
    envelope = read_object(path)
    if "snapshot" in envelope:
        snapshot = envelope["snapshot"]
        if not isinstance(snapshot, dict) or envelope.get("sha256") != digest(snapshot):
            raise ValueError(f"{path}: cohort snapshot hash mismatch")
        config = snapshot.get("campaign")
        if not isinstance(config, dict) or snapshot.get("config_sha256") != digest(config):
            raise ValueError(f"{path}: frozen campaign hash mismatch")
        return config, digest(config), envelope["sha256"]
    config = envelope.get("campaign")
    if not isinstance(config, dict) or envelope.get("sha256") != digest(config):
        raise ValueError(f"{path}: frozen campaign hash mismatch")
    return config, envelope["sha256"], None


def finite_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def output_cap(value) -> str:
    """Readable output-token cap: 128000 -> 128k, 32768 -> 32k."""
    if type(value) is not int or value <= 0:
        return "unrecorded"
    unit = next((unit for unit in (1000, 1024) if value % unit == 0), None)
    return f"{value // unit}k" if unit else str(value)


def campaign_cohort(config: dict) -> dict:
    """Experimental condition of one frozen campaign; distinct keys are never ranked together."""
    version = (config.get("prompts") or {}).get("version") or DEFAULT_PROMPT_VERSION
    schema = config.get("schema")
    if schema == "keygen-native-campaign-2":
        # Revision 2 models carry no tier and send no reasoning control.
        condition, text = "provider-default", "provider default effort"
    elif schema != "keygen-native-campaign-3":
        return {**UNIDENTIFIED_COHORT, "label": f"unidentified cohort (unsupported campaign schema {schema})"}
    elif str(config.get("campaign_id") or "").startswith(MAX_TIER_PREFIX):
        condition, text = "highest-declared-tier", "highest declared tier per exact route"
    else:
        condition, text = "declared-tier", "declared tier per exact route"
    return {"key": f"{condition}/{version}", "condition": condition, "prompt_version": version,
            "label": f"{text}, {version}"}


def tier_label(model: dict, condition: str) -> str:
    cap = output_cap((model.get("effective_settings") or {}).get("output_limit"))
    if condition == "provider-default":
        return f"provider default effort, {cap} output"
    if condition == "unidentified":
        return f"unidentified condition, {cap} output"
    tier = model.get("tier")
    level = tier.get("level") if isinstance(tier, dict) else None
    prefix = "highest declared tier" if condition == "highest-declared-tier" else "declared tier"
    return f"{prefix}: {level or 'undeclared'}, {cap} output"


def metadata(path: Path) -> tuple[dict, str | None]:
    try:
        return read_object(path), None
    except (OSError, ValueError, TypeError) as exc:
        return {}, f"{path.name}: {type(exc).__name__}: {exc}"


def identity(model: dict, fingerprint: str, kind: str) -> dict:
    return {"model_id": model.get("id"), "model": model.get("model"),
            "route": {key: model.get(key) for key in ROUTE_KEYS},
            "effective_settings": model.get("effective_settings"),
            "cohort_fingerprint": fingerprint, "kind": kind}


def cached_profile(directory: Path, status: dict, status_sha256: str | None = None) -> tuple[dict, str | None]:
    profile, error = metadata(directory / "profile.json")
    if error:
        return {}, error
    if (profile.get("evaluation_schema") != 2 or not isinstance(profile.get("score_version"), str)
            or type(profile.get("eligible")) is not bool or profile.get("cacheable") is not True):
        return profile, "retained profile is unsupported or marked non-cacheable; explicit evaluation required"
    expected = ((profile.get("inputs") or {}).get("artifacts") or {}).get("status.json")
    actual = status_sha256 or (hashlib.sha256((directory / "status.json").read_bytes()).hexdigest() if status else None)
    if expected != actual or expected is None:
        return profile, "retained profile does not match current status metadata"
    if profile.get("model") != (status.get("model") or {}).get("model"):
        return profile, "retained profile model differs from status metadata"
    if profile.get("status") != status.get("status"):
        return profile, "retained profile outcome differs from status metadata"
    if profile.get("eligible") and not finite_number((profile.get("craft") or {}).get("craft_score")):
        return profile, "eligible retained profile has no finite diagnostic score"
    return profile, None


def evaluated_status(status: dict, profile: dict) -> tuple[dict, str] | None:
    """The status a completed evaluation pinned, when a later FINALIZATION_ERROR overwrote it.

    Runners before the archive/evaluation split rewrote status.json after any finalization
    failure, including an artifact upload that failed after profile.json was written. The
    profile pins the SHA-256 of the status it evaluated; rebuilding exactly that status from
    the overwritten one proves the evaluation finished first, so the failure is post-evaluation.
    """
    if status.get("status") != "FINALIZATION_ERROR" or not isinstance(status.get("finalization_error"), dict):
        return None
    candidate = {key: value for key, value in status.items() if key != "finalization_error"}
    candidate.update(status=profile.get("status"), eligible=profile.get("eligible"),
                     failure_category=profile.get("run_failure_category"))
    payload = (json.dumps(candidate, indent=2, allow_nan=False) + "\n").encode()
    sha256 = hashlib.sha256(payload).hexdigest()
    expected = ((profile.get("inputs") or {}).get("artifacts") or {}).get("status.json")
    return (candidate, sha256) if sha256 == expected else None


def operator_cancellation(directory: Path, attempt_id: str, status: dict) -> tuple[dict | None, str | None]:
    """An operator cancellation recorded beside an attempt, with its true failure category.

    The frozen runner stops a model's sequence only on QUOTA/AUTH/CONTENT_FILTER, so an operator
    cancellation that had to stop the sequence is carried by one of those categories; the
    record names that vehicle and the real (INFRA) category reported instead.
    """
    path = directory / "operator-cancellation.json"
    if not path.exists():
        return None, None
    record, error = metadata(path)
    if error:
        return None, error
    if (record.get("action") != "operator_cancelled" or record.get("attempt_id") != attempt_id
            or record.get("true_failure_category") != "INFRA" or record.get("model_failure") is not False
            or record.get("recorded_failure_category_vehicle") != status.get("failure_category")):
        return None, "operator cancellation record does not match this attempt"
    return record, None


def attempt_row(root: Path, attempt_id: str, declared: tuple[dict, int] | None,
                selected_fingerprint: str, selected_hash: str, selected_cohort: dict) -> dict:
    directory = root / attempt_id
    status, status_error = metadata(directory / "status.json")
    model = status.get("model")
    model = model if isinstance(model, dict) else (declared[0] if declared else {})
    errors = [status_error] if status_error else []
    fingerprint = f"unknown:{attempt_id}"
    config_hash = None
    frozen_model = None
    row_cohort = UNIDENTIFIED_COHORT
    try:
        attempt_config, config_hash, snapshot_hash = read_cohort(directory / "campaign.json")
        fingerprint = snapshot_hash or config_hash
        row_cohort = campaign_cohort(attempt_config)
        frozen_model = next((entry for entry in attempt_config.get("models", []) if entry.get("id") == model.get("id")), None)
        if frozen_model != model:
            errors.append("status model settings differ from the frozen attempt campaign")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"campaign.json: {type(exc).__name__}: {exc}")
    if not directory.exists() and declared:
        fingerprint = selected_fingerprint
        config_hash = selected_hash
        frozen_model = declared[0]
        row_cohort = selected_cohort
    kind = "exhibition" if status.get("exhibition") else ("native" if config_hash else "unidentified")
    tier = tier_label(frozen_model or model, row_cohort["condition"])
    if kind == "exhibition":
        row_cohort = {**row_cohort, "key": f"exhibition/{row_cohort['key']}", "condition": "exhibition",
                      "label": f"exhibition, not a comparative native run ({row_cohort['label']})"}
    row_identity = identity(model, fingerprint, kind)
    skipped = status.get("status") == "SKIPPED_AFTER_SUCCESS"
    profile, profile_error = ({}, None) if skipped else cached_profile(directory, status)
    recorded_status = status.get("status", "MISSING")
    post_evaluation_error = None
    if profile_error and (recovered := evaluated_status(status, profile)):
        post_evaluation_error = status["finalization_error"]
        status, status_sha256 = recovered
        profile, profile_error = cached_profile(directory, status, status_sha256)
    if profile_error:
        errors.append(profile_error)
    finalization_error = status.get("finalization_error")
    if (directory / "finalization-error.json").exists():
        marker, marker_error = metadata(directory / "finalization-error.json")
        finalization_error = marker or marker_error or "finalization failed"
    if post_evaluation_error is not None:
        post_evaluation_error, finalization_error = finalization_error, None
    if finalization_error:
        errors.append(f"finalization error: {finalization_error}")
    cancellation, cancellation_error = operator_cancellation(directory, attempt_id, status)
    if cancellation_error:
        errors.append(cancellation_error)
    declared_match = bool(declared and model == declared[0] and config_hash == selected_hash
                          and fingerprint == selected_fingerprint and kind == "native"
                          and status.get("repetition", declared[1]) == declared[1]
                          and status.get("retry_of") is None)
    metadata_valid = (not status_error and frozen_model == model
                      and status.get("attempt_id") == attempt_id
                      and type(status.get("repetition")) is int
                      and status.get("status") not in PENDING_STATUSES)
    if status and not metadata_valid:
        errors.append("attempt metadata is incomplete, nonterminal or differs from its immutable identity")
    totals = status.get("totals") if isinstance(status.get("totals"), dict) and not skipped else None
    usage = totals or {}
    category = status.get("failure_category") or profile.get("run_failure_category")
    evaluation_category = (profile.get("evaluation_error") or {}).get("category")
    if cancellation:
        vehicle = cancellation["recorded_failure_category_vehicle"]
        category = cancellation["true_failure_category"]
        evaluation_category = category if evaluation_category == vehicle else evaluation_category
    if evaluation_category in NON_MODEL_FAILURES:
        category = category or evaluation_category
    if finalization_error:
        category = category or "EVAL"
    protocol_error = any(usage.get(key) for key in
                         ("identity_mismatch", "settings_mismatch", "identity_unverified", "gateway_error"))
    eligible = bool(metadata_valid and not errors and not skipped
                    and status.get("status") == "RENDERED_UNSCORED"
                    and status.get("render") == "ok" and status.get("eligible") is True
                    and not category and not status.get("error") and not status.get("cleanup_error")
                    and not status.get("trajectory_recovery_error")
                    and not status.get("finalization_error") and not protocol_error
                    and not (status.get("termination") or {}).get("failure_category")
                    and not (status.get("termination") or {}).get("error")
                    and status.get("model_failure") is not True
                    and profile.get("eligible") is True
                    and profile.get("evaluation_status") == "evaluated"
                    and not profile.get("evaluation_error") and not profile.get("run_failure_category")
                    and profile.get("model_failure") is not True)
    cost = usage.get("cost")
    cost = cost if finite_number(cost) and not skipped else None
    attempted = status.get("status") not in {"MISSING", "RESERVED", "SKIPPED_AFTER_SUCCESS", None}
    usage_unknown = bool(attempted and (totals is None or usage.get("usage_unknown")
                         or usage.get("in_flight_usage_unknown") or status.get("status") == "RUNNING"))
    model_failure = profile.get("model_failure") if not profile_error else status.get("model_failure")
    model_failure = model_failure if type(model_failure) is bool and attempted else None
    if cancellation:
        model_failure = False
    evaluation_identity = {key: (profile.get("inputs") or {}).get(key) for key in
                           ("scorer", "references", "analysis_renderer", "preview_encoder", "numerical")}
    evaluation_fingerprint = digest({"score_version": profile.get("score_version"),
                                     "schema": profile.get("evaluation_schema"), "inputs": evaluation_identity}) if profile else None
    terminal = status.get("status") not in PENDING_STATUSES and status.get("status") is not None
    outcome = ("SKIPPED" if skipped else "SUCCESS" if eligible else
               "FAILURE" if attempted and terminal and
               (category or status.get("error") or finalization_error or
                (not profile_error and profile.get("eligible") is False)) else "UNKNOWN")
    return {**row_identity, "group_id": digest(row_identity), "attempt_id": attempt_id, "run_dir": attempt_id,
            "cohort": row_cohort, "tier": tier,
            "repetition": status.get("repetition", declared[1] if declared else None),
            "retry_of": status.get("retry_of"), "predeclared": declared is not None,
            "declared_condition_match": declared_match,
            "status": "OPERATOR_CANCELLED" if cancellation else status.get("status", "MISSING"),
            "recorded_status": recorded_status,
            "operator_cancellation": cancellation["reason"] if cancellation else None,
            "attempted": attempted, "terminal": terminal, "outcome": outcome,
            "selected_attempt_id": status.get("selected_attempt_id"), "selected": False,
            "eligible": eligible, "failure_category": category, "model_failure": model_failure,
            "evaluation_error_category": evaluation_category,
            "finalization_error": finalization_error,
            "post_evaluation_finalization_error": post_evaluation_error,
            "craft": (profile.get("craft") or {}).get("craft_score") if eligible else None,
            "score_version": profile.get("score_version"), "evaluation_fingerprint": evaluation_fingerprint,
            "evaluation_status": "not_attempted" if skipped else profile.get("evaluation_status") if not profile_error else "unavailable_cache",
            "evaluation_location": profile.get("evaluation_location"),
            "totals": totals, "usage_unknown": usage_unknown, "cost": cost,
            "cost_unknown": bool(attempted and (cost is None or usage_unknown)),
            "wall_s": None if skipped else status.get("wall_seconds"),
            "error": "; ".join(errors + ([status["error"]] if status.get("error") else [])),
            "profile": profile}


def counts(rows: list[dict]) -> dict:
    attempted = [row for row in rows if row["attempted"]]
    return {"slots": len(rows), "attempts": len(attempted),
            "skipped_after_success": sum(row["status"] == "SKIPPED_AFTER_SUCCESS" for row in rows),
            "unattempted_slots": sum(not row["attempted"] for row in rows),
            "eligible_evaluations": sum(row["eligible"] for row in rows),
            "null_scores": sum(row["craft"] is None for row in rows),
            "model_failures": sum(row["model_failure"] is True and row["failure_category"] not in NON_MODEL_FAILURES for row in attempted),
            "model_failure_denominator": sum(row["model_failure"] is not None and row["failure_category"] not in NON_MODEL_FAILURES for row in attempted),
            "infrastructure_failures": sum(row["failure_category"] in NON_MODEL_FAILURES for row in attempted),
            "evaluation_failures": sum(row["evaluation_error_category"] == "EVAL" or bool(row["finalization_error"]) for row in attempted),
            "unknown_model_outcomes": sum(row["model_failure"] is None for row in attempted),
            "failure_categories": dict(sorted(Counter(row["failure_category"] for row in attempted if row["failure_category"]).items())),
            "evaluation_error_categories": dict(sorted(Counter(row["evaluation_error_category"] for row in attempted if row["evaluation_error_category"]).items())),
            "unknown_cost_attempts": sum(row["cost_unknown"] for row in attempted)}


def build_report(root: Path, cohort: Path) -> dict:
    root, cohort = Path(root).resolve(), Path(cohort).resolve()
    if not root.is_dir():
        raise ValueError(f"{root}: input root is not a directory")
    config, config_hash, snapshot_hash = read_cohort(cohort)
    # Revision 2 cohorts are historical; revision 3 adds declared tiers and key pools.
    if (config.get("schema") not in {"keygen-native-campaign-2", "keygen-native-campaign-3"}
            or type(config.get("max_attempts")) is not int or config["max_attempts"] != 3):
        raise ValueError("Publication requires a frozen native campaign with at most three sequential attempts")
    if (config.get("policies") or {}).get("attempt_selection") != ATTEMPT_SELECTION:
        raise ValueError("Campaign must select the first success and preserve every predetermined attempt slot")
    lock = root / "campaign.lock.json"
    if lock.exists():
        _, root_config_hash, root_snapshot_hash = read_cohort(lock)
        if root_config_hash != config_hash or (snapshot_hash and snapshot_hash != root_snapshot_hash):
            raise ValueError("Input root belongs to a different frozen cohort")
        snapshot_hash = root_snapshot_hash
    fingerprint = snapshot_hash or config_hash
    campaign = campaign_cohort(config)
    declared = {}
    for model in config.get("models", []):
        if (not isinstance(model, dict) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", model.get("id", ""))
                or not isinstance(model.get("effective_settings"), dict)
                or not all(isinstance(model.get(key), str) for key in ("model", *ROUTE_KEYS))):
            raise ValueError("Campaign model identity, route and effective settings must be explicit")
        for repetition in range(1, 4):
            attempt_id = f"{model['id']}-rep-{repetition}"
            if attempt_id in declared:
                raise ValueError("Duplicate predeclared attempt ID")
            declared[attempt_id] = (model, repetition)
    if not declared:
        raise ValueError("Campaign has no predeclared model roster")
    discovered = {path.name for path in root.iterdir() if path.is_dir() and not path.is_symlink()
                  and any((path / name).is_file() for name in ("status.json", "profile.json", "campaign.json"))}
    rows = []
    for attempt_id in sorted(declared.keys() | discovered):
        directory = root / attempt_id
        if directory.is_symlink():
            raise ValueError(f"{attempt_id}: attempt directory must not be a symlink")
        rows.append(attempt_row(root, attempt_id, declared.get(attempt_id), fingerprint, config_hash, campaign))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["group_id"], []).append(row)
    groups = []
    for group_id, attempts in grouped.items():
        first = attempts[0]
        originals = sorted((row for row in attempts if row["predeclared"]), key=lambda row: row["repetition"])
        successes = [row for row in originals if row["declared_condition_match"] and row["eligible"]]
        selected = successes[0] if successes else None
        if selected:
            selected["selected"] = True
        policy_errors = []
        for row in originals:
            if row["status"] == "SKIPPED_AFTER_SUCCESS":
                valid_skip = bool(selected and row["declared_condition_match"]
                                  and row["repetition"] > selected["repetition"]
                                  and row["selected_attempt_id"] == selected["attempt_id"])
                row["skip_link_valid"] = valid_skip
                if not valid_skip:
                    policy_errors.append(f"{row['attempt_id']}: skipped slot has no matching earlier eligible success")
            elif selected and row["attempted"] and row["repetition"] > selected["repetition"]:
                policy_errors.append(f"{row['attempt_id']}: attempted after the first success; retained but not selected")
        declared_group = bool(originals)
        state = ("success" if selected else
                 "interrupted" if any(row["status"] == "INTERRUPTED" for row in originals) else
                 "exhausted" if len(originals) == 3 and all(row["declared_condition_match"] and row["outcome"] == "FAILURE" for row in originals) else
                 "pending" if declared_group else "not_in_campaign")
        groups.append({"group_id": group_id, **{key: first[key] for key in
                       ("model_id", "model", "route", "effective_settings", "cohort_fingerprint", "kind", "cohort", "tier")},
                       **counts(attempts), "attempt_ids": [row["attempt_id"] for row in attempts],
                       "predeclared_slots": len(originals), "predeclared_eligible": len(successes),
                       "extra_attempts": len(attempts) - len(originals),
                       "attempted_count": sum(row["attempted"] for row in originals),
                       "state": state, "selected_attempt_id": selected["attempt_id"] if selected else None,
                       "selected_attempt_ordinal": selected["repetition"] if selected else None,
                       "selected_craft": selected["craft"] if selected else None,
                       "selected_evaluation_fingerprint": selected["evaluation_fingerprint"] if selected else None,
                       "policy_errors": policy_errors,
                       "summary_source": "first eligible success among matching predetermined sequential attempts",
                       "summary_note": "Adaptive stopping does not support independent-trial median, range or ranking claims."})
        for row in attempts:
            row["selection_state"] = state
            row["campaign_attempted_count"] = sum(item["attempted"] for item in originals)
            row["first_success_attempt_id"] = selected["attempt_id"] if selected else None
    groups.sort(key=lambda group: (group["cohort"]["key"] != campaign["key"], group["cohort"]["key"],
                                   str(group["model"]), group["group_id"]))
    tables = {}
    for group in groups:
        tables.setdefault(group["cohort"]["key"], {"cohort": group["cohort"], "group_ids": []})["group_ids"].append(group["group_id"])
    return {"schema": SCHEMA, "root": str(root), "cohort_input": str(cohort),
            "cohort": campaign, "cohort_tables": list(tables.values()),
            "tier_note": TIER_NOTE, "sample_note": SAMPLE_NOTE,
            "campaign_id": config.get("campaign_id"), "campaign_sha256": config_hash,
            "cohort_fingerprint": fingerprint, "max_attempts": 3, "attempt_selection": ATTEMPT_SELECTION,
            "score_role": SCORE_ROLE,
            "selection_note": "Select the earliest eligible success only. Retain all attempted outcomes and explicit unused slots. No best-of, latest-attempt, median or ranking claim.",
            "counts": counts(rows), "declared_counts": counts([row for row in rows if row["predeclared"]]),
            "groups": groups, "rows": rows}


def artifact_url(root: Path, directory: Path, relative: str, output: Path) -> str | None:
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        return None
    if not path.is_relative_to(root):
        return None
    prefix = Path(os.path.relpath(root, output.parent)).as_posix()
    return quote(f"{prefix}/{path.relative_to(root).as_posix()}", safe="/")


def page_rows(report: dict, output: Path) -> list[dict]:
    root = Path(report["root"])
    rows = []
    for row in report["rows"]:
        profile = row["profile"]
        directory = root / row["run_dir"]
        loop = profile.get("loop") or {}
        preview = loop.get("preview") or {}
        artifacts = [("original WAV", "canonical/canonical.wav"), ("video", "visualizer/visualizer.mp4"),
                     ("xm", "submission/tune.xm"), ("trajectory", "trajectory.json"), ("status", "status.json"),
                     ("profile / diagnostic evidence", "profile.json"), ("worker.log", "worker.log")]
        for label, path in (("loop excerpt (lossless)", preview.get("path")), ("loop trace", loop.get("trace_path")),
                            ("loop evidence", loop.get("evidence_path"))):
            if isinstance(path, str):
                artifacts.append((label, path))
        files = {label: url for label, path in artifacts if (url := artifact_url(root, directory, path, output))}
        submission = directory / "submission"
        scripts = [url for path in sorted(submission.iterdir()) if path.suffix in (".py", ".sh", ".txt", ".md", ".json")
                   and (url := artifact_url(root, directory, f"submission/{path.name}", output))] if submission.is_dir() else []
        archive, _ = metadata(directory / "archive.json")
        archived = sorted(name for name in (archive.get("files") or {})
                          if not (directory / name).is_file()) if archive.get("verified") is True else []
        structure, audio = profile.get("structure") or {}, profile.get("audio") or {}
        craft = (profile.get("craft") or {}) if row["eligible"] else {}
        process = profile.get("process") or {}
        rows.append({**row, "id": row["attempt_id"], "budget": "frozen cohort",
                     "parts": craft.get("parts") or {}, "capped": craft.get("capped", False),
                     "caps": craft.get("caps") or [], "uncapped": craft.get("uncapped"), "score_note": craft.get("note") or "",
                     "content_score": craft.get("content_score"), "factors": craft.get("factors") or {},
                     "spectral": audio.get("spectral") or {}, "mix": profile.get("mix") or {}, "mix_error": profile.get("mix_error") or "",
                     "loop": loop, "loop_error": profile.get("loop_error") or "", "flags": profile.get("flags") or [],
                     "dur": audio.get("duration_seconds"), "lufs": audio.get("lufs_integrated"),
                     "chans": structure.get("channels_used"), "patterns": structure.get("distinct_patterns_in_order"),
                     "instr": structure.get("instruments_used"), "samples": structure.get("samples"),
                     "steps": (row["totals"] or {}).get("requests"), "min": row["wall_s"] / 60 if finite_number(row["wall_s"]) else None,
                     "attempts": int(row["attempted"]), "ft2": process.get("used_ft2_tools"), "raw_xm": process.get("wrote_xm_directly"),
                     "files": files, "scripts": scripts, "archived_artifacts": archived,
                     "artifact_note": "Archived artifacts are not restored for publication; unavailable local files have no playback/download link." if archived else "Links include only local files that exist."})
    return rows


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [finite_json(item) for item in value]
    return value


def write_output(path: Path, content: str) -> None:
    legacy = Path(__file__).resolve().parents[1] / "legacy"
    if path.resolve().is_relative_to(legacy):
        raise ValueError("Legacy publication assets are read-only")
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        pending.write_text(content, encoding="utf-8")
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="One cohort's attempt directory")
    parser.add_argument("--cohort", type=Path, required=True, help="Frozen campaign envelope or campaign.lock.json")
    parser.add_argument("--out", type=Path, required=True, help="JSON report output")
    parser.add_argument("--html", type=Path, help="Optional existing-layout HTML publication")
    args = parser.parse_args()
    report = build_report(args.root, args.cohort)
    write_output(args.out.resolve(), json.dumps(finite_json(report), indent=2, allow_nan=False) + "\n")
    if args.html:
        output = args.html.resolve()
        def script_json(value) -> str:
            return json.dumps(finite_json(value), allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
        summary = html.escape(json.dumps({"campaign": report["campaign_id"], "cohort": report["cohort"], "counts": report["counts"], "groups": report["groups"]}, indent=2))
        page = (PAGE.replace("__DATA__", script_json(page_rows(report, output)))
                .replace("__COHORTS__", script_json([table["cohort"] for table in report["cohort_tables"]]))
                .replace("__SUMMARY__", summary)
                .replace("__TIER_NOTE__", html.escape(TIER_NOTE)).replace("__SAMPLE_NOTE__", html.escape(SAMPLE_NOTE)))
        write_output(output, page)
    print(f"{len(report['rows'])} attempt slots, {report['counts']['eligible_evaluations']} eligible diagnostics -> {args.out}")


if __name__ == "__main__":
    main()
