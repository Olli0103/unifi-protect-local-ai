"""Explicit, read-only reconciliation of one failed empty-draft reservation.

The tagged artifact source stays unchanged. Repaired workflow policy is pinned
separately, and its actual digest remains part of the signed candidate.
No create, edit, delete, rerun, token handling or approval operation lives here.
"""
from __future__ import annotations

import argparse
import hashlib
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
        gate.require(not env.get("RELEASE_RECOVERY_PREFLIGHT_RUN"),
                     "release_recovery_original_inputs_required")
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



def step_name_digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def job_graph(value, gate, *, recorded=False):
    rows = value.get("jobs")
    gate.require(isinstance(rows, list) and len(rows) == 8
                 and type(value.get("total_count")) is int and value["total_count"] == len(rows),
                 "release_recovery_preflight_jobs_incomplete")
    result = []
    for row in rows:
        gate.require(isinstance(row, dict) and type(row.get("id")) is int and row["id"] > 0
                     and row.get("status") == "completed" and isinstance(row.get("name"), str)
                     and isinstance(row.get("steps"), list) and len(row["steps"]) <= 80,
                     "release_recovery_preflight_jobs_refused")
        # Provider step names can include absolute runner paths. Keep only exact
        # UTF-8 digests in the reviewed record, not build-environment strings.
        steps = []
        for step in row["steps"]:
            name_key = "name_sha256" if recorded else "name"
            gate.require(isinstance(step, dict)
                         and (not recorded or set(step) ==
                              {"number", "name_sha256", "status", "conclusion"})
                         and isinstance(step.get(name_key), str)
                         and (not recorded or gate.HASH.fullmatch(step[name_key])),
                         "release_recovery_preflight_steps_refused")
            steps.append({**{key: step[key] for key in ("number", "status", "conclusion")},
                          "name_sha256": step[name_key] if recorded else
                          step_name_digest(step[name_key])})
        gate.require(all(type(step["number"]) is int and step["number"] > 0
                         and step["status"] == "completed"
                         for step in steps)
                     and len({step["number"] for step in steps}) == len(steps),
                     "release_recovery_preflight_steps_refused")
        result.append({**{key: row[key] for key in ("id", "name", "status", "conclusion")},
                       "steps": steps})
    gate.require(len({row["id"] for row in result}) == 8
                 and len({row["name"] for row in result}) == 8,
                 "release_recovery_preflight_jobs_refused")
    return sorted(result, key=lambda row: row["id"])


def reconciled_preflight(policy, revision, origin, release_id, current, gate, env, run):
    """Opt in to one separately reviewed, exact no-registry failed-run record.

    The policy-side record is reviewed with the repair, never read from the old
    artifact source. Live run/job metadata must still be identical. Unknown later
    dispatches and reruns remain refused by the complete history check.
    """
    requested_run = env.get("RELEASE_RECOVERY_PREFLIGHT_RUN", "")
    if not requested_run:
        return None
    requested_run = identifier(requested_run, gate)
    gate.require(requested_run not in {origin, current}, "release_recovery_preflight_identity_refused")
    record = gate.load(gate.read(policy / "docs/legal/recovery-prepush-reconciliation.json"))
    gate.require(set(record) == {"schema", "original_run_id", "reservation_id", "source_revision",
                                "run_id", "policy_revision", "workflow_sha256", "jobs"}
                 and record["schema"] == "aikey-prepush-reconciliation/2"
                 and record["original_run_id"] == origin
                 and type(record["reservation_id"]) is int and record["reservation_id"] == release_id
                 and record["source_revision"] == revision and record["run_id"] == requested_run
                 and isinstance(record["policy_revision"], str) and gate.SHA.fullmatch(record["policy_revision"])
                 and isinstance(record["workflow_sha256"], str) and gate.HASH.fullmatch(record["workflow_sha256"]),
                 "release_recovery_preflight_record_refused")
    previous = original_run(policy, requested_run, gate, run)
    gate.require(previous["head_sha"] == record["policy_revision"],
                 "release_recovery_preflight_policy_mismatch")
    workflow = run(["git", "show", previous["head_sha"] + ":.github/workflows/publish-release.yml"], cwd=policy)
    gate.require(hashlib.sha256(workflow.encode()).hexdigest() == record["workflow_sha256"],
                 "release_recovery_preflight_workflow_mismatch")
    response = gate.load(run(["gh", "api", f"repos/{gate.REPOSITORY}/actions/runs/{requested_run}/jobs?per_page=100"], cwd=policy))
    observed = job_graph(response, gate)
    expected = job_graph({"total_count": 8, "jobs": record["jobs"]}, gate, recorded=True)
    gate.require(observed == expected, "release_recovery_preflight_graph_changed")
    names = {row["name"]: row for row in observed}
    expected_jobs = {"qualify": "success", "reserve": "success", "sources": "success",
                     "packages": "failure", "images (amd64, ubuntu-24.04)": "failure",
                     "images (arm64, ubuntu-24.04-arm)": "failure", "assemble": "skipped", "publish": "skipped"}
    gate.require({name: row["conclusion"] for name, row in names.items()} == expected_jobs
                 and not names["assemble"]["steps"] and not names["publish"]["steps"],
                 "release_recovery_preflight_effects_not_excluded")
    for name, row in names.items():
        if not name.startswith("images ("):
            continue
        states = {step["name_sha256"]: step["conclusion"] for step in row["steps"]}
        gate.require(len(states) == len(row["steps"])
                     and states.get(step_name_digest("Bind pre-push intent to tested image configs and inventories")) == "failure"
                     and states.get(step_name_digest("Short-lived workflow registry login")) == "skipped"
                     and states.get(step_name_digest("Push only these attempt-specific images; observe immutable manifests")) == "skipped"
                     and states.get(step_name_digest("Remove owned local fixtures and verify zero remaining resources")) == "success",
                     "release_recovery_preflight_effects_not_excluded")
    return {"run_id": requested_run, "workflow_revision": previous["head_sha"],
            "created_at": previous["created_at"], "updated_at": previous["updated_at"],
            "jobs_sha256": hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest()}

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
                 and set(names) in (
                     {"qualify", "reserve", "sources", "packages", "images", "assemble", "publish"},
                     {"qualify", "reserve", "sources", "packages", "images (amd64)",
                      "images (arm64)", "assemble", "publish"}),
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
    preflight = reconciled_preflight(policy, revision, origin, release_id, current, gate, env, run)
    allowed = {int(origin), int(current)}
    if preflight is not None:
        listing_by_id = {item["id"]: item for item in runs}
        prior = listing_by_id.get(int(preflight["run_id"]), {})
        active = listing_by_id[int(current)]
        gate.require(prior.get("head_sha") == preflight["workflow_revision"]
                     and prior.get("run_attempt") == 1 and type(prior.get("run_attempt")) is int
                     and prior.get("status") == "completed" and prior.get("conclusion") == "failure"
                     and created(original.get("created_at"), gate) < created(preflight["created_at"], gate)
                     <= created(preflight["updated_at"], gate) < created(active.get("created_at"), gate),
                     "release_recovery_preflight_history_refused")
        allowed.add(int(preflight["run_id"]))
    origin_time = created(original.get("created_at"), gate)
    # created_at never changes on rerun. Require an older, terminal, single
    # attempt whose entire observed activity ended before the original dispatch.
    # Unknown or repeated attempts require deliberate reconciliation, not adoption.
    def older_attempt_is_closed(item):
        return (
            type(item.get("run_attempt")) is int and item["run_attempt"] == 1
            and item.get("status") == "completed"
            and created(item.get("created_at"), gate)
            <= created(item.get("run_started_at"), gate)
            <= created(item.get("updated_at"), gate) < origin_time
        )

    gate.require(all(item["id"] in allowed
                     or older_attempt_is_closed(item) for item in runs),
                 "release_recovery_intervening_dispatch_requires_reconciliation")
    # Both the unchanged artifact source and repaired execution policy need
    # their own exact-head seven-job qualification; neither substitutes for the other.
    gate.continuous_integration(policy, policy_revision, run)
    result = {
        "schema": "aikey-release-recovery/1",
        "original_run_id": origin,
        "reservation_id": release_id,
        "source_revision": revision,
        "workflow_revision": policy_revision,
        "workflow_run_id": current,
        "profile": profile,
    }
    if preflight is not None:
        result["reconciled_preflight"] = preflight
    return result


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
