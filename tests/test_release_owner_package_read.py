"""Fictional owner-token replies and immutable seven-job early-failure replay."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_release_publication import publication
from test_release_recovery import recovery, gate

private = gate.private_registry_module()
ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ["gh", "api", "--paginate", "--slurp",
             "user/packages?package_type=container&per_page=100"]
DIRECT = ["gh", "api", "user/packages/container/local-aikey-0.1.0a1"]
VERSIONS = ["gh", "api", "--paginate", "--slurp",
            "user/packages/container/local-aikey-0.1.0a1/versions?per_page=100"]


@pytest.mark.parametrize("argv", [CATALOGUE, VERSIONS, DIRECT])
def test_owner_namespace_is_selected_only_after_exact_owner_identity(tmp_path, monkeypatch, argv):
    monkeypatch.setenv("RELEASE_PACKAGES_READ_TOKEN", "FICTIONAL_OWNER_READER")
    calls = []
    def run(command, **options):
        calls.append(command)
        assert options["env"]["GH_TOKEN"] == "FICTIONAL_OWNER_READER"
        response = ({"login": gate.OWNER, "id": gate.OWNER_ID, "type": "User"}
                    if command == ["gh", "api", "user"] else [[]])
        options["stdout"].write(json.dumps(response).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(publication.subprocess, "run", run)
    assert publication.package_metadata(argv, cwd=tmp_path) == "[[]]"
    assert calls == [["gh", "api", "user"], argv]


@pytest.mark.parametrize("route", [
    "users/Olli0103/packages?package_type=container&per_page=100",
    "users/Olli0103/packages/container/local-aikey-0.1.0a1/versions?per_page=100",
    "user/packages/container/foreign/versions?per_page=100",
    "user/packages?package_type=container&per_page=100&page=2",
    "https://example.invalid/user/packages",
])
def test_public_namespace_and_nonallowlisted_routes_never_receive_token(tmp_path, monkeypatch, route):
    monkeypatch.setenv("RELEASE_PACKAGES_READ_TOKEN", "FICTIONAL_OWNER_READER")
    monkeypatch.setattr(publication.subprocess, "run", lambda *a, **k: pytest.fail("transport"))
    with pytest.raises(ValueError, match="command_refused"):
        publication.package_metadata(CATALOGUE[:-1] + [route], cwd=tmp_path)


def test_private_shared_package_is_not_looked_up_in_public_namespace(tmp_path):
    from test_release_private_recovery import packet, version
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if argv == DIRECT:
            return json.dumps({"name": "local-aikey-0.1.0a1", "package_type": "container",
                                  "visibility": "private", "repository": {"full_name": gate.REPOSITORY}})
        if argv == VERSIONS:
            return json.dumps([[version()]])
        return "[[]]"  # A public-namespace success does not observe this private package.
    publication.private_images(tmp_path, packet(), run=run)
    assert calls == [DIRECT, VERSIONS]


STEP_NAMES = (
    "Set up job", "Exact dispatch source, no persisted Git credentials", "Python 3.12",
    "Resolve unchanged source or explicit original-run recovery",
    "Exact artifact source separate from workflow policy", "Set runner-local source delivery path",
    "Read-only readiness; publishing is opt-in",
    "Verify package catalogue access before any staging or native build",
    "Post Exact artifact source separate from workflow policy", "Post Python 3.12",
    "Post Exact dispatch source, no persisted Git credentials", "Complete job",
)


@pytest.mark.parametrize("fault", [
    "none", "record_hash", "extra_record", "record_policy", "changed_workflow", "wrong_policy",
    "rerun", "active", "foreign_owner", "missing_job", "extra_job", "duplicate_job", "wrong_count",
    "changed_step", "step_number", "probe_success", "reserve_started", "hidden_steps",
    "effects_relabelled", "wrong_source", "wrong_origin", "wrong_release", "current_reused",
])
@pytest.mark.parametrize("followup", [False, True])
def test_exact_early_failure_never_hides_downstream_effects(tmp_path, fault, followup):
    run_id = private.OWNER_READ_FOLLOWUP_RUN if followup else private.OWNER_READ_RUN
    policy_revision = private.OWNER_READ_FOLLOWUP_POLICY if followup else private.OWNER_READ_POLICY
    filename = "recovery-private-owner-followup.json" if followup else "recovery-private-owner-read.json"
    record = json.loads((ROOT / "docs/legal" / filename).read_text())
    jobs = copy.deepcopy(record["record"]["jobs"])
    names = {hashlib.sha256(name.encode()).hexdigest(): name for name in STEP_NAMES}
    for row in jobs:
        for step in row["steps"]:
            step["name"] = names[step.pop("name_sha256")]
    person = {"login": gate.OWNER, "id": gate.OWNER_ID, "type": "User"}
    observed = {"id": int(run_id), "event": "workflow_dispatch",
                "path": ".github/workflows/publish-release.yml", "head_branch": "main",
                "head_sha": policy_revision, "status": "completed", "conclusion": "failure",
                "run_attempt": 1, "actor": person, "triggering_actor": copy.deepcopy(person),
                "repository": {"full_name": gate.REPOSITORY},
                "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:01:00Z"}
    previous = b"FICTIONAL preceding incident record"
    workflow = "FICTIONAL exact policy workflow"
    record["previous_record_sha256"] = hashlib.sha256(previous).hexdigest()
    record["record"]["workflow_sha256"] = hashlib.sha256(workflow.encode()).hexdigest()
    count = 7
    source, origin, release, current = private.SOURCE, private.ORIGIN_RUN, 444049704, "99999999999"
    qualify = next(row for row in jobs if row["name"] == "qualify")
    probe = next(s for s in qualify["steps"] if s["name"].startswith("Verify package catalogue"))
    if fault == "record_hash":
        record["previous_record_sha256"] = "0" * 64
    elif fault == "extra_record":
        record["automatic_retry"] = True
    elif fault == "record_policy":
        record["record"]["policy_revision"] = "a" * 40
    elif fault == "changed_workflow":
        workflow += "changed"
    elif fault == "wrong_policy":
        observed["head_sha"] = "a" * 40
    elif fault == "rerun":
        observed["run_attempt"] = 2
    elif fault == "active":
        observed["status"] = "in_progress"
    elif fault == "foreign_owner":
        observed["actor"] = {"login": "FICTIONAL", "id": 1, "type": "User"}
    elif fault == "missing_job":
        jobs.pop()
    elif fault == "extra_job":
        jobs.append(copy.deepcopy(jobs[-1]))
    elif fault == "duplicate_job":
        jobs[-1] = copy.deepcopy(jobs[0])
    elif fault == "wrong_count":
        count = 8
    elif fault == "changed_step":
        probe["name"] += " altered"
    elif fault == "step_number":
        probe["number"] += 100
    elif fault == "probe_success":
        probe["conclusion"] = "success"
    elif fault == "reserve_started":
        jobs[1]["conclusion"] = "success"
    elif fault == "hidden_steps":
        jobs[1]["steps"] = [copy.deepcopy(probe)]
    elif fault == "effects_relabelled":
        record["effects"]["previous_incident_unchanged"] = False
    elif fault == "wrong_source":
        source = "a" * 40
    elif fault == "wrong_origin":
        origin = "123"
    elif fault == "wrong_release":
        release = 123
    elif fault == "current_reused":
        current = run_id
    proxy = SimpleNamespace(**vars(gate))
    proxy.read = lambda path: (json.dumps(record).encode()
                               if path.name == filename else previous)
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "git":
            return workflow
        return json.dumps({"total_count": count, "jobs": jobs}
                          if "/jobs?" in argv[-1] else observed)
    if fault == "none":
        result = private.owner_read_context(tmp_path, source, origin, release, current, proxy, run, recovery, followup=followup)
        assert result["run_id"] == run_id
    else:
        with pytest.raises(ValueError):
            private.owner_read_context(tmp_path, source, origin, release, current, proxy, run, recovery, followup=followup)
    assert all(c[0] == "git" or c[:2] == ["gh", "api"] for c in calls)
