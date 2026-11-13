"""Explicit, read-only reconciliation of one failed empty-draft reservation.

The tagged artifact source stays unchanged. Repaired workflow policy is pinned
separately, and its actual digest remains part of the signed candidate.
No create, edit, delete, rerun, token handling or approval operation lives here.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re


def identifier(value, gate):
    gate.require(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,19}", value),
                 "release_recovery_identifier_refused")
    return value


def requested(env, gate):
    origin = env.get("RELEASE_RECOVERY_RUN", "")
    release_id = env.get("RELEASE_RECOVERY_ID", "")
    if not origin and not release_id:
        return None
    return identifier(origin, gate), int(identifier(release_id, gate))


def created(value, gate):
    gate.require(isinstance(value, str)
                 and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value),
                 "release_recovery_timestamp_refused")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def original_run(root, origin, gate, run):
    value = gate.load(run(["gh", "api",
                          f"repos/{gate.REPOSITORY}/actions/runs/{origin}"], cwd=root))
    gate.require(
        type(value.get("id")) is int and str(value["id"]) == origin
        and value.get("event") == "workflow_dispatch"
        and value.get("path") == ".github/workflows/publish-release.yml"
        and value.get("head_branch") == "main"
        and isinstance(value.get("head_sha"), str) and gate.SHA.fullmatch(value["head_sha"])
        and value.get("status") == "completed" and value.get("conclusion") == "failure"
        and type(value.get("run_attempt")) is int and value["run_attempt"] == 1,
        "release_recovery_original_run_refused")
    for field in ("actor", "triggering_actor"):
        person = value.get(field)
        gate.require(isinstance(person, dict) and person.get("login") == gate.OWNER
                     and type(person.get("id")) is int and person["id"] == gate.OWNER_ID
                     and person.get("type") == "User", "release_recovery_original_owner_refused")
    repository = value.get("repository")
    gate.require(isinstance(repository, dict) and repository.get("full_name") == gate.REPOSITORY,
                 "release_recovery_original_repository_refused")
    return value


def policy_context(gate, env, run):
    root = Path(__file__).resolve().parents[1]
    revision = run(["git", "rev-parse", "HEAD"], cwd=root).strip()
    gate.require(isinstance(revision, str) and gate.SHA.fullmatch(revision),
                 "release_recovery_policy_revision_refused")
    current = gate.workflow_context(env, revision)
    gate.require(not run(["git", "status", "--porcelain", "--untracked-files=all"],
                         cwd=root).strip(), "release_recovery_policy_not_clean")
    return root, revision, current


def resolve(gate, env, run):
    policy, revision, current = policy_context(gate, env, run)
    request = requested(env, gate)
    if request is None:
        return revision
    origin, _ = request
    gate.require(origin != current, "release_recovery_same_run_refused")
    return original_run(policy, origin, gate, run)["head_sha"]


def context(root, revision, gate, env, run, *, profile):
    request = requested(env, gate)
    if request is None:
        gate.workflow_context(env, revision)
        return None
    origin, release_id = request
    gate.require(profile == "image", "release_recovery_profile_unsupported")
    policy, policy_revision, current = policy_context(gate, env, run)
    gate.require(origin != current, "release_recovery_same_run_refused")
    original = original_run(root, origin, gate, run)
    gate.require(original["head_sha"] == revision, "release_recovery_source_mismatch")
    jobs = gate.load(run(["gh", "api",
                          f"repos/{gate.REPOSITORY}/actions/runs/{origin}/jobs?per_page=100"],
                         cwd=root))
    values = jobs.get("jobs")
    gate.require(isinstance(values, list) and 2 <= len(values) <= 16
                 and type(jobs.get("total_count")) is int and jobs["total_count"] == len(values)
                 and all(isinstance(item, dict) and type(item.get("id")) is int
                         and item["id"] > 0 and item.get("status") == "completed"
                         for item in values)
                 and len({item["id"] for item in values}) == len(values),
                 "release_recovery_original_jobs_incomplete")
    names = [item.get("name") for item in values]
    gate.require(all(isinstance(name, str) for name in names)
                 and len(set(names)) == len(names)
                 and set(names) <= {"qualify", "reserve", "sources", "packages", "images",
                                    "images (amd64)", "images (arm64)", "assemble", "publish"}
                 and {"qualify", "reserve"} <= set(names),
                 "release_recovery_original_jobs_refused")
    gate.require(all(item.get("conclusion") ==
                     ("success" if item["name"] == "qualify" else
                      "failure" if item["name"] == "reserve" else "skipped")
                     for item in values), "release_recovery_prior_effects_not_excluded")
    # The first controlled recovery is not permission to repeat a failed recovery.
    # Complete dispatch history must exclude every intervening attempt, including
    # unknown/read-only dispatches whose inputs are not available in this API.
    listing = gate.load(run(["gh", "api",
                            f"repos/{gate.REPOSITORY}/actions/workflows/publish-release.yml/runs"
                            "?event=workflow_dispatch&per_page=100"], cwd=root))
    runs = listing.get("workflow_runs")
    gate.require(isinstance(runs, list) and 1 <= len(runs) <= 100
                 and type(listing.get("total_count")) is int
                 and listing["total_count"] == len(runs)
                 and all(isinstance(item, dict) and type(item.get("id")) is int
                         and item["id"] > 0 for item in runs)
                 and len({item["id"] for item in runs}) == len(runs)
                 and int(origin) in {item["id"] for item in runs}
                 and int(current) in {item["id"] for item in runs},
                 "release_recovery_history_incomplete")
    origin_time = created(original.get("created_at"), gate)
    gate.require(all(item["id"] in {int(origin), int(current)}
                     or created(item.get("created_at"), gate) < origin_time for item in runs),
                 "release_recovery_intervening_dispatch_requires_reconciliation")
    # Both the unchanged artifact source and repaired execution policy need
    # their own exact-head seven-job qualification; neither substitutes for the other.
    gate.continuous_integration(policy, policy_revision, run)
    return {
        "schema": "aikey-release-recovery/1",
        "original_run_id": origin,
        "reservation_id": release_id,
        "source_revision": revision,
        "workflow_revision": policy_revision,
        "workflow_run_id": current,
        "profile": profile,
    }


def main(argv=None):
    import release_prepare as gate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("resolve",))
    parser.parse_args(argv)
    try:
        revision = resolve(gate, os.environ, gate.command)
        output = os.environ.get("GITHUB_OUTPUT")
        gate.require(output and Path(output).is_file(), "release_recovery_output_required")
        with open(output, "a", encoding="utf-8") as target:
            target.write("source_revision=" + revision + "\n")
        print(json.dumps({"source_revision": revision, "mutated": False}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        code = (error.args[0] if isinstance(error, gate.PreparationError) and error.args
                else "release_recovery_unavailable")
        import sys
        refusal = json.dumps({"error": code, "mutated": False, "automatic_retry": False})
        print(refusal)
        print(refusal, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
