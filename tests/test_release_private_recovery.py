"""Fictional provider responses; historical facts are tested, never relabelled."""
import copy
import json
from pathlib import Path
import types

import pytest

from test_release_prepare import gate
from test_release_candidate import candidate, native_attempt  # noqa: F401

private = gate.private_registry_module()


def packet():
    return {
        "tag": "v0.1.0a1", "version": "0.1.0a1", "workflow_run_id": "99999999999",
        "source_revision": private.SOURCE,
        "images": {p: private.DESTINATION for p in ("aikey", "aiport")},
        "recovery": {
            "original_run_id": private.ORIGIN_RUN, "source_revision": private.SOURCE,
            "workflow_run_id": "99999999999",
            "reservation_id": 444049704,
            "private_registry": {
                "schema": "aikey-private-registry-recovery/1",
                "incident_run_id": private.INCIDENT_RUN, "destination": private.DESTINATION,
                "tag_layout": "profile-version-architecture-run",
                "old_tag": private.OLD_TAG, "old_digest": private.OLD_DIGEST,
                "old_cleanup": "failed-not-reused",
                "public_phase": "occurred-downloads-not-excluded",
            },
        },
    }


def version():
    return {"id": 1573317107, "name": private.OLD_DIGEST,
            "metadata": {"container": {"tags": [private.OLD_TAG]}}}


def test_profiles_and_architectures_cannot_overwrite_each_other_or_incident():
    plan = packet()
    refs = {candidate.tagged(plan, p, a) for p in ("aikey", "aiport")
            for a in (None, "amd64", "arm64")}
    assert len(refs) == 6
    assert all(x.startswith(private.DESTINATION + ":") for x in refs)
    assert not any(x.endswith(private.OLD_TAG) for x in refs)
    for ref in refs:
        seen = []
        candidate.observed_tag(Path("."), ref,
                               run=lambda argv, root: seen.append(argv) or b'{"schemaVersion":2}')
        assert len(seen) == 1


@pytest.mark.parametrize("field", [
    "schema", "incident_run_id", "destination", "tag_layout", "old_tag", "old_digest",
    "old_cleanup", "public_phase",
])
def test_changed_incident_layout_never_grants_destination_authority(field):
    plan = packet()
    plan["recovery"]["private_registry"][field] = "FICTIONAL-other"
    with pytest.raises(ValueError, match="layout_refused"):
        private.layout(plan, gate)


@pytest.mark.parametrize("fault", [
    "none", "empty", "bad_page", "duplicate_id", "missing_old", "changed_old_digest",
    "changed_old_id", "changed_old_tags", "foreign_tag", "foreign_run", "untagged",
    "duplicate_tag", "bad_digest", "duplicate_json_key",
])
def test_full_version_catalogue_retains_old_effect_and_rejects_unknowns(tmp_path, fault):
    plan = packet()
    rows = [version()]
    current = {"id": 2, "name": "sha256:" + "f" * 64,
               "metadata": {"container": {"tags": ["aiport-0.1.0a1-amd64-run99999999999"]}}}
    rows.append(current)
    if fault == "empty":
        rows.clear()
    elif fault == "duplicate_id":
        current["id"] = rows[0]["id"]
    elif fault == "missing_old":
        rows.pop(0)
    elif fault == "changed_old_digest":
        rows[0]["name"] = "sha256:" + "e" * 64
    elif fault == "changed_old_id":
        rows[0]["id"] = 7
    elif fault == "changed_old_tags":
        rows[0]["metadata"]["container"]["tags"].append("aiport-0.1.0a1-index-run99999999999")
    elif fault == "foreign_tag":
        current["metadata"]["container"]["tags"] = ["latest"]
    elif fault == "foreign_run":
        current["metadata"]["container"]["tags"] = ["aiport-0.1.0a1-amd64-run123"]
    elif fault == "untagged":
        current["metadata"]["container"]["tags"] = []
    elif fault == "duplicate_tag":
        current["metadata"]["container"]["tags"] *= 2
    elif fault == "bad_digest":
        current["name"] = "FICTIONAL"
    raw = json.dumps([rows[:1], rows[1:]] if fault != "bad_page" else [{}])
    if fault == "duplicate_json_key":
        raw = raw.replace('"id": 2', '"id": 1, "id": 2')
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        return raw
    if fault == "none":
        private.private_versions(tmp_path, plan, gate, run)
    else:
        with pytest.raises(ValueError):
            private.private_versions(tmp_path, plan, gate, run)
    assert len(calls) == 1 and "--paginate" in calls[0]
    assert not any(x in calls[0] for x in ("POST", "DELETE", "PATCH", "PUT"))


def test_one_existing_package_qualifies_both_profiles_but_public_missing_never_does(tmp_path):
    plan = packet()
    for fault in ("none", "public", "missing", "repository"):
        packages = [{"name": "local-aikey-0.1.0a1", "package_type": "container",
                     "visibility": "private", "repository": {"full_name": gate.REPOSITORY}}]
        if fault == "public":
            packages[0]["visibility"] = "public"
        elif fault == "missing":
            packages.clear()
        elif fault == "repository":
            packages[0]["repository"]["full_name"] = "FICTIONAL/other"
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return json.dumps([[version()]] if "/versions?" in argv[-1] else
                              packages[0] if packages else {})
        if fault == "none":
            candidate.publication.private_images(tmp_path, plan, run=run)
            assert len(calls) == 2
        else:
            with pytest.raises(ValueError):
                candidate.publication.private_images(tmp_path, plan, run=run)
            assert len(calls) == 1


def test_exact_record_reconciles_failed_cleanup_without_inventing_success(tmp_path):
    original = json.loads((Path(__file__).resolve().parents[1] /
                           "docs/legal/recovery-private-registry.json").read_text())
    record = copy.deepcopy(original)
    prior = b'{"FICTIONAL":"previous-reviewed-chain"}'
    import hashlib
    record["previous_record_sha256"] = hashlib.sha256(prior).hexdigest()
    class Recovery:
        @staticmethod
        def original_run(*args):
            return {"head_sha": private.POLICY, "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:01:00Z"}
        @staticmethod
        def job_graph(value, gate, **kwargs):
            return value["jobs"]
        @staticmethod
        def step_name_digest(name):
            return hashlib.sha256(name.encode()).hexdigest()
    fake_gate = types.SimpleNamespace(**vars(gate))
    fake_gate.read = lambda path: prior if path.name == "recovery-package-read.json" else json.dumps(record).encode()
    record["record"]["workflow_sha256"] = hashlib.sha256(b"FICTIONAL-workflow").hexdigest()
    def run(argv, **kwargs):
        return ("FICTIONAL-workflow" if argv[0] == "git" else
                json.dumps({"jobs": original["record"]["jobs"]}))
    result = private.context(tmp_path, private.SOURCE, private.ORIGIN_RUN, 444049704,
                             "99999999999", fake_gate, run, Recovery)
    assert result["run_id"] == private.INCIDENT_RUN
    for field, value in [("cleanup", {"amd64": "success", "arm64": "success"}),
                         ("public_phase", "no-effects"), ("old_tag_mutation", True),
                         ("old_runner_reuse", True), ("old_artifact_reuse", True)]:
        record["effects"][field] = value
        with pytest.raises(ValueError, match="effects_refused"):
            private.context(tmp_path, private.SOURCE, private.ORIGIN_RUN, 444049704,
                            "99999999999", fake_gate, run, Recovery)
        record["effects"] = copy.deepcopy(original["effects"])


@pytest.mark.parametrize("fault", ["observe", "config", "privacy"])
def test_failed_postpush_check_still_removes_only_current_local_alias(native_attempt, fault):  # noqa: F811
    root, plan, results, inspected, _, inspect = native_attempt
    intent = root.parent / "intent.json"
    candidate.image_intent(root, plan, results, "amd64", intent,
                           qualified=results.parent / "qualified", run=inspect)
    calls = []
    def run(argv, root, **kwargs):
        calls.append(argv)
        if argv[:3] == ["docker", "image", "inspect"]:
            return inspect(argv, root)
        if argv[:3] == ["docker", "buildx", "imagetools"]:
            if fault == "observe":
                raise candidate.publication.PublicationError("release_registry_observation_unavailable")
            return json.dumps({"schemaVersion": 2, "config": {"digest":
                "sha256:" + "0" * 64 if fault == "config" else inspected["aikey"]["Id"]}}).encode()
        return b""
    def metadata(argv, **kwargs):
        rows = [{"name": x.rsplit("/", 1)[1], "package_type": "container",
                 "visibility": "public" if fault == "privacy" and any(
                     x[:3] == ["docker", "image", "push"] for x in calls) else "private",
                 "repository": {"full_name": gate.REPOSITORY}} for x in plan["images"].values()]
        return json.dumps([rows])
    with pytest.raises(ValueError):
        candidate.push_images(root, plan, intent, "amd64", results, root.parent / "out.json",
                              run=run, metadata_run=metadata)
    removals = [x for x in calls if x[:3] == ["docker", "image", "rm"]]
    assert removals == [["docker", "image", "rm", candidate.tagged(plan, "aikey", "amd64")]]
    assert len([x for x in calls if x[:3] == ["docker", "image", "push"]]) == 1
    assert not (root.parent / "out.json").exists()
