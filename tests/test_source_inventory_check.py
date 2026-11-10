"""Synthetic source bytes and package metadata; no downloads or extraction."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("source_inventory_check", TOOLS / "source_inventory_check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
sys.path.pop(0)


def bundle(tmp_path):
    root = tmp_path / "sources"
    (root / "python").mkdir(parents=True)
    raw = b"fictional original source bytes"
    (root / "python/example.tar.gz").write_bytes(raw)
    row = dict(path="python/example.tar.gz", component="Example_Package", version="1.0",
               upstream_url="https://example.invalid/source", sha256=hashlib.sha256(raw).hexdigest(),
               size=len(raw))
    manifest = dict(schema="selected-upstream-source-delivery/1", files=[row], file_count=1,
                    bytes=len(raw), release_approved=False, complete_corresponding_source=False)
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    return root, check.file_digest(path), manifest


def component(name, version, kind, **props):
    return dict(name=name, version=version, properties=[
        {"name": key, "value": value} for key, value in
        {"syft:package:type": kind, **props}.items()])


def test_original_bytes_and_python_name_normalization(tmp_path):
    root, sha, _ = bundle(tmp_path)
    index, count, size = check.read_sources(root, sha)
    row = check.match(component("example.package", "1.0", "python"), index)
    assert row["status"] == "archive_candidate"
    assert row["files"] == ["python/example.tar.gz"]
    assert count == 1 and size > 0
    assert check.match(component("example-package", "2.0", "python"), index)["status"] == "needs_evidence"


def test_debian_explicit_source_version_not_binary_version():
    index = {("debian", "bash", "5.2.15-2"): ["debian/bash/source.dsc"]}
    row = check.match(component("bash", "5.2.15-2+b13", "deb",
        **{"syft:metadata:source": "bash", "syft:metadata:sourceVersion": "5.2.15-2"}), index)
    assert row["files"] and row["source_version"] == "5.2.15-2"
    assert not check.match(component("bash", "5.2.15-2+b13", "deb"), index)["files"]


def test_no_cross_ecosystem_or_binary_name_inference():
    index = {("rust", "openssl", "1"): ["rust/openssl.crate"],
             ("python", "openssl", "1"): ["python/openssl.tar.gz"]}
    assert not check.match(component("openssl", "1", "deb"), index)["files"]
    assert not check.match(component("openssl", "1", "binary"), index)["files"]
    assert not check.match(component("local-aikey", "0.1.0", "python"), index)["files"]


@pytest.mark.parametrize("fault", ["bytes", "manifest", "duplicate", "escape", "symlink", "parent_link"])
def test_changed_or_redirected_sources_refused(tmp_path, fault):
    root, sha, manifest = bundle(tmp_path)
    if fault == "bytes":
        (root / "python/example.tar.gz").write_bytes(b"changed")
    elif fault == "manifest":
        (root / "manifest.json").write_text("{}")
    elif fault == "duplicate":
        manifest["files"].append(deepcopy(manifest["files"][0]))
        manifest["file_count"] = 2
    elif fault == "escape":
        manifest["files"][0]["path"] = "../outside"
    elif fault == "symlink":
        target = root / "python/example.tar.gz"
        target.rename(root / "original")
        target.symlink_to(root / "original")
    elif fault == "parent_link":
        (root / "python").rename(root / "redirected")
        (root / "python").symlink_to(root / "redirected")
    if fault in {"duplicate", "escape"}:
        (root / "manifest.json").write_text(json.dumps(manifest))
        sha = check.file_digest(root / "manifest.json")
    with pytest.raises(check.CheckError):
        check.read_sources(root, sha)


def test_duplicate_source_property_refused():
    value = component("bash", "1", "deb", **{"syft:metadata:source": "bash"})
    value["properties"].append({"name": "syft:metadata:source", "value": "other"})
    with pytest.raises(check.CheckError, match="ambiguous"):
        check.match(value, {})


def test_missing_architecture_refused(tmp_path):
    root, sha, _ = bundle(tmp_path)
    with pytest.raises(check.CheckError, match="matrix_incomplete"):
        check.review(root, sha, [], "a" * 40)


def matrix(tmp_path):
    directories = []
    revision = 'a' * 40
    for arch in ('amd64', 'arm64'):
        directory = tmp_path / arch
        directory.mkdir()
        directories.append(directory)
        profiles = {}
        for profile in ('aikey', 'aiport'):
            subject = dict(revision=revision, architecture=arch, nonce='fixture-' + arch,
                           profile=profile, image_id='sha256:' + 'b' * 64)
            package = component('example-package', '1.0', 'python')
            package.update({'bom-ref': 'fixture-package', 'type': 'library'})
            sbom = dict(bomFormat='CycloneDX', components=[package,
                dict(type='operating-system', name='debian', version='12')])
            sbom_path = directory / (profile + '-sbom.cdx.json')
            sbom_path.write_text(json.dumps(sbom))
            sbom_sha = check.file_digest(sbom_path)
            licenses = dict(schema='aikey-image-license-review/2', **subject,
                native_report_sha256='c' * 64, sbom_sha256=sbom_sha,
                packages=[dict(name='example-package', version='1.0', type='python',
                               purl=None, licenses=[])], texts={}, notice_files=[],
                licenses_reviewed=False, release_approved=False)
            license_path = directory / (profile + '-licenses.json')
            license_path.write_text(json.dumps(licenses))
            profiles[profile] = dict(schema='aikey-image-inventory/2', **subject,
                sbom_sha256=sbom_sha, license_review_sha256=check.file_digest(license_path),
                licenses_reviewed=False, release_approved=False, conversion_verified=True,
                operating_system=dict(id='debian', version='12'), package_count=1,
                license_texts_retained=0, license_text_bytes=0)
        inventory = dict(schema='aikey-image-inventory-summary/2', architecture=arch,
            revision=revision, nonce='fixture-' + arch, profiles=profiles,
            cleanup_verified=True, install_cases_finished=8,
            release_approved=False, licenses_reviewed=False)
        (directory / 'image-inventory.json').write_text(json.dumps(inventory))
    return directories, revision


def test_four_image_matrix_and_stale_revision_are_distinct(tmp_path):
    root, sha, _ = bundle(tmp_path)
    directories, revision = matrix(tmp_path)
    result = check.review(root, sha, directories, revision)
    assert result['current_revision'] and len(result['images']) == 4
    assert all(i['counts'] == {'archive_candidate': 1} for i in result['images'])
    assert result['release_approved'] is False
    assert result['complete_corresponding_source'] is False
    stale = check.review(root, sha, directories, 'd' * 40)
    assert not stale['current_revision']
    assert all(not i['current_revision'] for i in stale['images'])


@pytest.mark.parametrize('fault', ['sbom', 'license', 'wrong_profile', 'cleanup', 'duplicate_arch'])
def test_matrix_tampering_refused(tmp_path, fault):
    root, sha, _ = bundle(tmp_path)
    directories, revision = matrix(tmp_path)
    if fault in {'sbom', 'license'}:
        filename = 'aikey-sbom.cdx.json' if fault == 'sbom' else 'aikey-licenses.json'
        path = directories[0] / filename
        path.write_bytes(path.read_bytes() + b' ')
    elif fault == 'duplicate_arch':
        directories[1] = directories[0]
    else:
        path = directories[0] / 'image-inventory.json'
        value = json.loads(path.read_text())
        if fault == 'cleanup':
            value['cleanup_verified'] = False
        else:
            value['profiles']['aikey']['profile'] = 'aiport'
        path.write_text(json.dumps(value))
    with pytest.raises(check.CheckError):
        check.review(root, sha, directories, revision)
