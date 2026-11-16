"""Finite incident recovery; preserve the old effects, never bootstrap a registry.

Both profiles use the already private package, with profile-specific attempt
tags. This is execution-policy metadata, not a change to the tagged source or
its legal/source attestations. Old runner cleanup remains FAILED, not repaired
retroactively; no old runner, image, tag, asset or signature is reused.
"""
from __future__ import annotations

import hashlib
import json
import re

INCIDENT_RUN = "43865727276"
OWNER_READ_RUN = "43887790289"
OWNER_READ_POLICY = "52689906c7910d9b71284ed40e3333d6db7c5799"
ORIGIN_RUN = "43402688428"
SOURCE = "a3da9c21715dade37fbe3a25529fa85fd17dc430"
POLICY = "e646efad5e9da4db7874ac79c6cbf58ed106b7b1"
DESTINATION = "ghcr.io/olli0103/local-aikey-0.1.0a1"
OLD_TAG = "0.1.0a1-arm64-run43865727276"
OLD_DIGEST = "sha256:09149304f23c25b107c3c1e213bedd199925ea95a5abdd7f5fb12a37418f513a"


def layout(plan, gate):
    recovery = plan.get("recovery")
    if not isinstance(recovery, dict) or "private_registry" not in recovery:
        return None
    value = recovery["private_registry"]
    expected = {"schema": "aikey-private-registry-recovery/1",
                "incident_run_id": INCIDENT_RUN, "destination": DESTINATION,
                "tag_layout": "profile-version-architecture-run",
                "old_tag": OLD_TAG, "old_digest": OLD_DIGEST,
                "old_cleanup": "failed-not-reused",
                "public_phase": "occurred-downloads-not-excluded"}
    gate.require(value == expected and recovery.get("original_run_id") == ORIGIN_RUN
                 and recovery.get("source_revision") == SOURCE
                 and recovery.get("reservation_id") == 444049704
                 and plan.get("source_revision") == SOURCE
                 and plan.get("workflow_run_id") == recovery.get("workflow_run_id")
                 and isinstance(plan.get("workflow_run_id"), str)
                 and re.fullmatch("[1-9][0-9]{0,19}", plan["workflow_run_id"])
                 and plan["workflow_run_id"] not in {INCIDENT_RUN, ORIGIN_RUN, OWNER_READ_RUN}
                 and plan.get("tag") == "v0.1.0a1" and plan.get("version") == "0.1.0a1",
                 "release_private_recovery_layout_refused")
    return dict(expected)


def context(policy, revision, origin, release_id, current, gate, run, recovery):
    """Check the exact terminal graph plus the preceding finite reviewed chain."""
    raw = gate.read(policy / "docs/legal/recovery-private-registry.json")
    record = gate.load(raw)
    previous_raw = gate.read(policy / "docs/legal/recovery-package-read.json")
    gate.require(set(record) == {"schema", "previous_record_sha256", "record", "effects"}
                 and record["schema"] == "aikey-private-registry-incident/1"
                 and record["previous_record_sha256"] == hashlib.sha256(previous_raw).hexdigest()
                 and revision == SOURCE and origin == ORIGIN_RUN and release_id == 444049704
                 and current not in {INCIDENT_RUN, ORIGIN_RUN, OWNER_READ_RUN},
                 "release_private_recovery_record_refused")
    facts = record["record"]
    gate.require(set(facts) == {"run_id", "policy_revision", "workflow_sha256", "jobs"}
                 and facts["run_id"] == INCIDENT_RUN and facts["policy_revision"] == POLICY,
                 "release_private_recovery_record_refused")
    observed_run = recovery.original_run(policy, INCIDENT_RUN, gate, run)
    gate.require(observed_run["head_sha"] == POLICY,
                 "release_private_recovery_policy_refused")
    workflow = run(["git", "show", POLICY + ":.github/workflows/publish-release.yml"], cwd=policy)
    gate.require(hashlib.sha256(workflow.encode()).hexdigest() == facts["workflow_sha256"],
                 "release_private_recovery_workflow_refused")
    api = gate.load(run(["gh", "api",
                         f"repos/{gate.REPOSITORY}/actions/runs/{INCIDENT_RUN}/jobs?per_page=100"],
                        cwd=policy))
    jobs = recovery.job_graph(api, gate)
    gate.require(jobs == recovery.job_graph({"total_count": 8, "jobs": facts["jobs"]},
                                            gate, recorded=True),
                 "release_private_recovery_graph_changed")
    expected = {"qualify": "success", "reserve": "success", "sources": "success",
                "packages": "success", "images (amd64, ubuntu-24.04)": "failure",
                "images (arm64, ubuntu-24.04-arm)": "failure",
                "assemble": "skipped", "publish": "skipped"}
    gate.require({row["name"]: row["conclusion"] for row in jobs} == expected,
                 "release_private_recovery_graph_refused")
    for row in jobs:
        if row["name"] in {"assemble", "publish"}:
            gate.require(not row["steps"], "release_private_recovery_downstream_refused")
        if not row["name"].startswith("images ("):
            continue
        states = {step["name_sha256"]: step["conclusion"] for step in row["steps"]}
        required = {
            "Bind pre-push intent to tested image configs and inventories": "success",
            "Short-lived workflow registry login": "success",
            "Push only these attempt-specific images; observe immutable manifests": "failure",
            "Remove owned local fixtures and verify zero remaining resources": "failure",
            "Retain only sanitized complete native handoff": "skipped",
        }
        gate.require(len(states) == len(row["steps"])
                     and all(states.get(recovery.step_name_digest(name)) == state
                             for name, state in required.items()),
                     "release_private_recovery_cleanup_record_refused")
    effects = {"package": "local-aikey-0.1.0a1", "version_id": 1573317107,
               "tag": OLD_TAG, "digest": OLD_DIGEST,
               "public_phase": "occurred-downloads-not-excluded",
               "contained_private_at": "2026-11-16T12:34:21Z",
               "cleanup": {"amd64": "failure", "arm64": "failure"},
               "old_runner_reuse": False, "old_artifact_reuse": False,
               "old_tag_mutation": False, "original_draft_uploaded_assets": 0}
    gate.require(record["effects"] == effects, "release_private_recovery_effects_refused")
    return {"run_id": INCIDENT_RUN, "workflow_revision": POLICY,
            "created_at": observed_run["created_at"], "updated_at": observed_run["updated_at"],
            "jobs_sha256": hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()}


def owner_read_context(policy, revision, origin, release_id, current, gate, run, recovery):
    """Admit only the exact read-only qualifier failure after the incident."""
    raw = gate.read(policy / "docs/legal/recovery-private-owner-read.json")
    record = gate.load(raw)
    previous = gate.read(policy / "docs/legal/recovery-private-registry.json")
    gate.require(set(record) == {"schema", "previous_record_sha256", "record", "effects"}
                 and record["schema"] == "aikey-private-owner-read-reconciliation/1"
                 and record["previous_record_sha256"] == hashlib.sha256(previous).hexdigest()
                 and revision == SOURCE and origin == ORIGIN_RUN and release_id == 444049704
                 and current not in {INCIDENT_RUN, ORIGIN_RUN, OWNER_READ_RUN},
                 "release_owner_read_record_refused")
    facts = record["record"]
    gate.require(set(facts) == {"run_id", "policy_revision", "workflow_sha256", "jobs"}
                 and facts["run_id"] == OWNER_READ_RUN
                 and facts["policy_revision"] == OWNER_READ_POLICY,
                 "release_owner_read_record_refused")
    observed = recovery.original_run(policy, OWNER_READ_RUN, gate, run)
    gate.require(observed["head_sha"] == OWNER_READ_POLICY,
                 "release_owner_read_policy_refused")
    workflow = run(["git", "show", OWNER_READ_POLICY + ":.github/workflows/publish-release.yml"],
                   cwd=policy)
    gate.require(hashlib.sha256(workflow.encode()).hexdigest() == facts["workflow_sha256"],
                 "release_owner_read_workflow_refused")
    api = gate.load(run(["gh", "api",
                         f"repos/{gate.REPOSITORY}/actions/runs/{OWNER_READ_RUN}/jobs?per_page=100"],
                        cwd=policy))
    jobs = recovery.job_graph(api, gate, early=True)
    gate.require(jobs == recovery.job_graph({"total_count": 7, "jobs": facts["jobs"]},
                                            gate, recorded=True, early=True),
                 "release_owner_read_graph_changed")
    expected = {"qualify": "failure", "reserve": "skipped", "sources": "skipped",
                "packages": "skipped", "images": "skipped", "assemble": "skipped",
                "publish": "skipped"}
    gate.require({row["name"]: row["conclusion"] for row in jobs} == expected,
                 "release_owner_read_graph_refused")
    for row in jobs:
        if row["name"] != "qualify":
            gate.require(not row["steps"], "release_owner_read_downstream_refused")
            continue
        states = {step["name_sha256"]: step["conclusion"] for step in row["steps"]}
        gate.require(len(states) == len(row["steps"])
                     and states.get(recovery.step_name_digest(
                         "Read-only readiness; publishing is opt-in")) == "success"
                     and states.get(recovery.step_name_digest(
                         "Verify package catalogue access before any staging or native build")) == "failure",
                     "release_owner_read_boundary_refused")
    gate.require(record["effects"] == {
        "qualify_failed_before_staging": True, "downstream_jobs_skipped": 6,
        "new_stage_approval": False, "release_uploaded_assets": 0,
        "registry_write_jobs_started": False, "previous_incident_unchanged": True},
        "release_owner_read_effects_refused")
    return {"run_id": OWNER_READ_RUN, "workflow_revision": OWNER_READ_POLICY,
            "created_at": observed["created_at"], "updated_at": observed["updated_at"],
            "jobs_sha256": hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()}


def private_versions(root, plan, gate, run):
    """Keep the known old version immutable; reject unreviewed registry versions.

    New tags are exclusively profile/architecture/current-run qualified. Full
    pagination includes untagged versions, so an empty/partial view is not proof.
    """
    if layout(plan, gate) is None:
        return
    pages = gate.load('{"pages":' + run(["gh", "api", "--paginate", "--slurp",
                           "user/packages/container/local-aikey-0.1.0a1/versions?per_page=100"],
                          cwd=root) + '}')["pages"]
    gate.require(isinstance(pages, list) and pages and all(isinstance(x, list) for x in pages),
                 "release_private_recovery_versions_incomplete")
    versions = [row for page in pages for row in page]
    gate.require(1 <= len(versions) <= 1024
                 and all(isinstance(row, dict) and type(row.get("id")) is int for row in versions)
                 and len({row["id"] for row in versions}) == len(versions),
                 "release_private_recovery_versions_refused")
    allowed = {f"{profile}-{plan['version']}-{arch}-run{plan['workflow_run_id']}"
               for profile in ("aikey", "aiport") for arch in ("amd64", "arm64", "index")}
    old = []
    for row in versions:
        tags = row.get("metadata", {}).get("container", {}).get("tags")
        gate.require(isinstance(tags, list) and tags and all(isinstance(x, str) for x in tags)
                     and len(set(tags)) == len(tags)
                     and re.fullmatch("sha256:[0-9a-f]{64}", row.get("name", "")),
                     "release_private_recovery_version_refused")
        if OLD_TAG in tags:
            gate.require(row["id"] == 1573317107 and row["name"] == OLD_DIGEST and tags == [OLD_TAG],
                         "release_private_recovery_old_version_changed")
            old.append(row)
        else:
            gate.require(set(tags) <= allowed, "release_private_recovery_unreviewed_version")
    gate.require(len(old) == 1, "release_private_recovery_old_version_missing")
