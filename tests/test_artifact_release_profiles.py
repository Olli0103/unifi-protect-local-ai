"""Artifact-scoped gates; every permission in these fixtures is fictional."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import community_release_check as community  # noqa: E402
import release_prepare as prepare  # noqa: E402
from test_release_prepare import tagged_source, decision  # noqa: E402,F401
from test_release_assets import real_packages, assets  # noqa: E402,F401
from test_release_candidate import candidate, assembly  # noqa: E402,F401


def verified():
    return {"schema": community.SCHEMA, "reviewed_snapshot_sha256": "fictional",
            "checks": {name: {"status": "verified", "reviewer": "FICTIONAL reviewer",
                              "evidence_ref": "FICTIONAL no real permission"}
                       for name in community.REQUIRED},
            "research_record": {"status": "needs_evidence"}}


def test_schema_one_migration_preserves_history_but_never_carries_approval():
    original = {"schema": "community-release-evidence/1",
                "checks": {name: {"status": "verified", "reviewer": "FICTIONAL",
                                  "evidence_ref": "FICTIONAL"}
                           for name in community.LEGACY_REQUIRED},
                "reviewed_snapshot_sha256": "old", **decision()}
    before = copy.deepcopy(original)
    migrated = community.migrate_evidence(original)
    assert original == before and migrated["legacy_evidence"] == original
    assert migrated["schema"] == community.SCHEMA
    assert migrated["reviewed_snapshot_sha256"] is None
    assert set(migrated["checks"]) == community.REQUIRED
    assert all(item == {"status": "needs_evidence", "reviewer": None, "evidence_ref": None}
               for item in migrated["checks"].values())
    assert migrated["publication"]["status"] == "needs_evidence"
    assert community.evidence_issues(original, "old", audit_only=False) == {"invalid_evidence_schema"}


@pytest.mark.parametrize("profile", ["package", "image"])
def test_exact_required_fields_and_snapshot_are_profile_scoped(profile):
    record = verified()
    record["checks"]["image_licenses"]["status"] = "needs_evidence"
    assert community.evidence_issues(record, "fictional", audit_only=False, profile=profile) == (
        set() if profile == "package" else {"needs_evidence:image_licenses"})
    assert "unreviewed_source_snapshot" in community.evidence_issues(
        record, "changed", audit_only=False, profile=profile)
    assert "needs_evidence:research_record" not in community.evidence_issues(
        record, "fictional", audit_only=False, profile=profile)


@pytest.mark.parametrize("field", sorted(community.PACKAGE_REQUIRED))
@pytest.mark.parametrize("fault", ["missing", "pending", "reviewer", "reference"])
def test_package_cannot_bypass_any_of_its_six_gates(field, fault):
    record = verified()
    if fault == "missing":
        del record["checks"][field]
    elif fault == "pending":
        record["checks"][field]["status"] = "needs_evidence"
    else:
        record["checks"][field]["reviewer" if fault == "reviewer" else "evidence_ref"] = " "
    assert community.evidence_issues(record, "fictional", audit_only=False, profile="package")


def test_actual_package_preparation_accepts_pending_image_gate_and_never_reads_registry(tagged_source):  # noqa: F811
    root, run, context, calls, _ = tagged_source
    path = root / "docs/legal/release-evidence.json"
    record = json.loads(path.read_text())
    record["checks"]["image_licenses"]["status"] = "needs_evidence"
    record["publication"]["images"] = {"aikey": None, "aiport": None}
    path.write_text(json.dumps(record))
    subprocess.run(["git", "-c", "user.name=Fictional", "-c", "user.email=fixture@example.invalid",
                    "commit", "-am", "Fictional package-only decision"], cwd=root, check=True,
                   capture_output=True)
    subprocess.run(["git", "tag", "-f", "v0.1.0rc1"], cwd=root, check=True, capture_output=True)
    context["GITHUB_SHA"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

    def current(argv, **kwargs):
        if argv[:2] == ["git", "ls-remote"]:
            return context["GITHUB_SHA"] + "\trefs/tags/v0.1.0rc1\n"
        if argv[:2] == ["gh", "api"] and "/workflows/" in argv[-1]:
            value = json.loads(run(argv, **kwargs))
            value["workflow_runs"][0]["head_sha"] = context["GITHUB_SHA"]
            return json.dumps(value)
        return run(argv, **kwargs)

    value = prepare.prepare(root, "v0.1.0rc1", publish=True, profile="package", env=context, run=current)
    assert value["images"] == {} and value["release_profile"] == "package"
    assert sum(len(row["job_ids"]) for row in value["continuous_integration"]) == 7
    with pytest.raises(prepare.PreparationError, match="non_audit"):
        prepare.prepare(root, "v0.1.0rc1", profile="image", env=context, run=current)
    assert not any("packages/container" in " ".join(call) for call in calls)


def test_package_candidate_reaches_final_consumer_without_docker_or_image_artifacts(assembly, monkeypatch):  # noqa: F811
    root, packet, inputs, destination, _ = assembly
    packet.update(images={}, release_profile="package")
    # Assert actual image helpers never execute, rather than accepting no-op mocks.
    def refused(*args, **kwargs):
        raise AssertionError("package-only path attempted Docker")
    monkeypatch.setattr(candidate.publication, "docker_read", refused)
    candidate.indexes(root, packet, inputs, destination, run=refused)
    assert candidate.push_indexes(root, packet, destination, run=refused) == {}
    candidate.finalize(root, packet, destination)
    (destination / "release-provenance.sigstore.json").write_text("FICTIONAL signature")
    observed = candidate.publication.checked_assets(destination, packet)
    assert observed["images"] == {}
    assert not any(name.startswith(("aikey-", "aiport-")) for name in observed["files"])
    with candidate.publication.snapshot_assets(destination, root, packet) as captured:
        assert candidate.publication.checked_assets(captured, packet) == observed
    # Cross-profile asset substitution is rejected before any upload.
    image_plan = dict(packet, images={"aikey": "ghcr.io/olli0103/fictional-key",
                                     "aiport": "ghcr.io/olli0103/fictional-port"})
    with pytest.raises(ValueError):
        candidate.publication.checked_assets(destination, image_plan)


def test_actual_cli_cannot_report_approval_with_pending_fields(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tools/community_release_check.py"), "--root", str(root),
         "--profile", "package"], cwd=tmp_path, text=True, capture_output=True, timeout=15)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["required_checks"] == sorted(community.PACKAGE_REQUIRED)
    assert not report["release_approved"]
    assert {row for row in report["issues"] if row.startswith("needs_evidence:")} == {
        "needs_evidence:" + field for field in community.PACKAGE_REQUIRED}
