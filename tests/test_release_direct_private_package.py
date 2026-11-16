"""Saved live diagnosis motivates direct reads; fixtures never contact GitHub."""
import copy
import json
from pathlib import Path

import pytest

from test_release_publication import publication
from test_release_private_recovery import packet, version

DIRECT = ["gh", "api", "user/packages/container/local-aikey-0.1.0a1"]
VERSIONS = ["gh", "api", "--paginate", "--slurp",
            "user/packages/container/local-aikey-0.1.0a1/versions?per_page=100"]


@pytest.mark.parametrize("fault", [
    "none", "public", "internal", "missing_visibility", "wrong_repo", "no_repo",
    "wrong_name", "no_name", "wrong_type", "list", "null", "scalar", "http404",
    "duplicate_key", "foreign_version", "missing_old_version", "unknown_tag",
])
def test_direct_object_still_requires_positive_privacy_and_exact_full_versions(tmp_path, fault):
    plan = packet()
    obj = {"name": "local-aikey-0.1.0a1", "package_type": "container", "visibility": "private",
           "repository": {"full_name": publication.gate.REPOSITORY}}
    versions = [version()]
    if fault in {"public", "internal"}:
        obj["visibility"] = fault
    elif fault == "missing_visibility":
        obj.pop("visibility")
    elif fault == "wrong_repo":
        obj["repository"]["full_name"] = "FICTIONAL/other"
    elif fault == "no_repo":
        obj["repository"] = None
    elif fault == "wrong_name":
        obj["name"] = "FICTIONAL-foreign"
    elif fault == "no_name":
        obj.pop("name")
    elif fault == "wrong_type":
        obj["package_type"] = "npm"
    elif fault == "list":
        obj = [obj]
    elif fault == "null":
        obj = None
    elif fault == "scalar":
        obj = "FICTIONAL-response"
    elif fault == "foreign_version":
        versions[0]["name"] = "sha256:" + "f" * 64
    elif fault == "missing_old_version":
        versions = []
    elif fault == "unknown_tag":
        row = copy.deepcopy(version())
        row.update(id=42, name="sha256:" + "f" * 64)
        row["metadata"]["container"]["tags"] = ["FICTIONAL-unreviewed-run"]
        versions.append(row)
    calls = []
    def read(argv, **kwargs):
        calls.append(argv)
        assert argv in (DIRECT, VERSIONS), "no namespace-list fallback or other endpoint"
        if argv == DIRECT:
            if fault == "http404":
                raise publication.PublicationError("release_package_metadata_http_404")
            raw = json.dumps(obj)
            return raw.replace('"visibility": "private"', '"visibility": "public", "visibility": "private"') if fault == "duplicate_key" else raw
        return json.dumps([versions])
    if fault == "none":
        publication.private_images(tmp_path, plan, run=read)
        assert calls == [DIRECT, VERSIONS]
    else:
        with pytest.raises(ValueError):
            publication.private_images(tmp_path, plan, run=read)
    assert not list(tmp_path.iterdir())
    assert calls[0] == DIRECT


def test_retained_actual_diagnostic_proves_read_scope_direct_private_and_omitted_lists():
    root = Path(__file__).resolve().parents[1]
    receipt = json.loads((root / "docs/legal/package-metadata-diagnostic.json").read_text())
    assert receipt["run_id"] == 43907939181 and receipt["job_id"] == 133441735101
    report = receipt["report"]
    assert report["owner_verified"] and not report["mutated"] and not report["release_ready"]
    for name in ("owner_default", "owner_private", "named_default"):
        assert report["requests"][name]["status"] == 200
        assert report["requests"][name]["rows"] == report["requests"][name]["target_matches"] == 0
        assert not report["requests"][name]["has_next"]
    obj = report["requests"]["package"]
    assert obj["status"] == 200 and obj["visibility"] == "private"
    assert obj["read_packages_scope"] and obj["scopes_header_present"]
    assert obj["target_name_matches"] and obj["container_type_matches"] and obj["repository_matches"]
    versions = report["requests"]["versions"]
    assert versions["status"] == 200 and versions["rows"] == 1
    assert versions["known_incident_id_present"] and not versions["has_next"]
