"""Fictional sources and inventories; no upload, native image or rights attestation."""
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import release_sources as sources  # noqa: E402
import render_image_sources as render  # noqa: E402
import image_sbom_check as image_check  # noqa: E402
from test_source_inventory_check import bundle, matrix  # noqa: E402
from test_release_publication import publication  # noqa: E402
from test_release_assets import assets, seal  # noqa: E402,F401


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "project"
    (root / "src/aikey").mkdir(parents=True)
    (root / "src/aikey/__init__.py").write_text('"""FICTIONAL SOURCE ONLY."""\n')
    (root / "LICENSE").write_text("FICTIONAL license fixture, no approval")
    (root / "pyproject.toml").write_text('[project]\nname="local-aikey"\nversion="0.1.0rc1"\n')
    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "user.name=FICTIONAL", "-c", "user.email=fixture@example.invalid", *args],
            cwd=root, text=True).strip()
    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "Fictional source fixture")
    revision = git("rev-parse", "HEAD")
    source_root, pin, _ = bundle(tmp_path)
    directories, _ = matrix(tmp_path)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for directory in directories:
        value = json.loads((directory / "image-inventory.json").read_text())
        value["revision"] = revision
        for profile, receipt in value["profiles"].items():
            receipt["revision"] = revision
            path = directory / (profile + "-licenses.json")
            license_data = json.loads(path.read_text())
            license_data["revision"] = revision
            path.write_text(json.dumps(license_data))
            receipt["license_review_sha256"] = sources.file_info(path)["sha256"]
        (directory / "image-inventory.json").write_text(json.dumps(value))
        (directory / "summary.json").write_text('{"fictional":true}')
        shutil.copytree(directory, inputs / ("container-install-" + directory.name))
    plan = {"source_revision": revision, "tag": "v0.1.0rc1", "source_date_epoch": 1700000000,
            "source_delivery": {"manifest_sha256": pin},
            "images": {"aikey": "ghcr.io/olli0103/local-aikey-0.1.0rc1", "aiport": "ghcr.io/olli0103/local-aiport-0.1.0rc1"}}
    return root, source_root, inputs, tmp_path / "delivery", plan


def test_complete_multipart_bundle_reruns_real_checker_and_binds_index_and_archive(fixture):
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan, part_limit=16384)
    assert 1 < len(value["parts"]) <= 8
    actual, report = sources.validate(root, target, plan)
    assert actual == value and report["current_revision"]
    assert report["release_approved"] is False and report["complete_corresponding_source"] is False
    assert len(report["images"]) == 4 and all(i["counts"] == {"archive_candidate": 1} for i in report["images"])
    record = sources.bundle_record(value, plan)
    assert record["sha256"] == sources.file_info(target / "source-bundle.json")["sha256"]
    assert record["archive_sha256"] == value["sha256"]
    assert all(p["url"].startswith("https://github.com/Olli0103/unifi-protect-local-ai/releases/download/v0.1.0rc1/")
               for p in record["parts"])
    assert publication.source_assets(target, plan) == {"source-bundle.json"} | {p["name"] for p in value["parts"]}


@pytest.mark.parametrize("fault", ["missing", "part", "digest", "revision", "pin", "symlink", "hardlink"])
def test_missing_or_changed_bundle_fails_before_delivery(fixture, fault):
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan)
    path = target / value["parts"][0]["name"]
    if fault == "missing":
        path.unlink()
    elif fault == "part":
        path.write_bytes(path.read_bytes() + b"changed")
    elif fault == "symlink":
        path.rename(target / "original")
        path.symlink_to(target / "original")
    elif fault == "hardlink":
        import os
        os.link(path, target / "linked")
    else:
        value[{"digest": "sha256", "revision": "revision", "pin": "manifest_sha256"}[fault]] = "0" * (40 if fault == "revision" else 64)
        (target / "source-bundle.json").write_text(json.dumps(value, indent=2) + "\n")
    with pytest.raises((ValueError, OSError)):
        sources.validate(root, target, plan)


@pytest.mark.parametrize("fault", ["stale_inventory", "missing_source", "wrong_manifest", "wrong_project"])
def test_source_checker_or_exact_project_refusal_precedes_bundle_success(fixture, fault):
    root, original, inputs, target, plan = fixture
    if fault == "missing_source":
        (original / "python/example.tar.gz").unlink()
    elif fault == "wrong_manifest":
        plan["source_delivery"]["manifest_sha256"] = "0" * 64
    elif fault == "wrong_project":
        plan["source_revision"] = "0" * 40
    else:
        p = inputs / "container-install-arm64/image-inventory.json"
        value = json.loads(p.read_text())
        value["revision"] = "0" * 40
        p.write_text(json.dumps(value))
    with pytest.raises((ValueError, OSError)):
        sources.build(root, original, inputs, target, plan)
    assert not (target / "source-bundle.json").exists()


@pytest.mark.parametrize("member", ["../escape", "/absolute", "sources/link", "sources/duplicate"])
def test_archive_path_link_and_duplicate_refusals(fixture, member):
    import io
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        info = tarfile.TarInfo(member)
        if member == "sources/link":
            info.type, info.linkname = tarfile.SYMTYPE, "/outside"
            archive.addfile(info)
        else:
            info.size = 1
            archive.addfile(info, io.BytesIO(b"x"))
            if member == "sources/duplicate":
                archive.addfile(info, io.BytesIO(b"x"))
    data = raw.getvalue()
    for part in value["parts"]:
        (target / part["name"]).unlink()
    name = sources.NAME + ".part001"
    (target / name).write_bytes(data)
    info = sources.file_info(target / name)
    value.update(sha256=info["sha256"], parts=[dict(name=name, **info)])
    (target / "source-bundle.json").write_text(json.dumps(value, indent=2) + "\n")
    with pytest.raises(ValueError, match="member_refused"):
        sources.validate(root, target, plan)
    assert not (target.parent / "escape").exists()


def test_rendered_notice_is_required_in_native_collector_and_not_a_default_source_offer():
    template = (Path(__file__).resolve().parents[1] / "docs/legal/image-sources-template.md").read_text()
    url = "https://github.com/Olli0103/unifi-protect-local-ai/releases/download/v0.1.0a1/release.json"
    raw = render.render(template, url).encode()
    row = {"path": image_check.SOURCE_NOTICE, "sha256": image_check.digest(raw),
           "size": len(raw), "base64": base64.b64encode(raw).decode()}
    image_check.require_source_notice([row])
    with pytest.raises(ValueError, match="missing"):
        image_check.require_source_notice([])
    assert "UNPUBLISHED" in render.render(template, "")
    for bad in ["https://other.invalid/source", url + "\nBAD", "file:///source", url.replace("release.json", "../release.json")]:
        with pytest.raises(ValueError):
            render.render(template, bad)
    project = Path(__file__).resolve().parents[1]
    for name in ["Dockerfile", "Dockerfile.aiport-candidate"]:
        recipe = (project / name).read_text()
        assert "ARG SOURCE_BUNDLE_URL\n" in recipe
        assert "ARG SOURCE_BUNDLE_URL=" not in recipe
        assert "/usr/share/local-aikey/SOURCES.md" in recipe


def test_image_consumer_refuses_missing_source_bundle(fixture):
    _, _, _, target, plan = fixture
    target.mkdir()
    with pytest.raises(OSError):
        publication.source_assets(target, plan)


def test_same_inode_change_after_part_check_is_rejected_by_whole_archive_hash(fixture, monkeypatch):
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan)
    path = target / value['parts'][0]['name']
    real_open = sources.checked_file
    visits = 0
    def race_open(candidate, limit=sources.TOTAL_LIMIT):
        nonlocal visits
        if Path(candidate) == path:
            visits += 1
            if visits == 2:
                raw = path.read_bytes()
                path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        return real_open(candidate, limit)
    monkeypatch.setattr(sources, 'checked_file', race_open)
    with pytest.raises(ValueError, match='digest_mismatch'):
        sources.validate(root, target, plan)
    assert visits == 2


def test_fifo_source_part_is_rejected_without_waiting_for_a_writer(fixture):
    import os
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan)
    path = target / value['parts'][0]['name']
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(ValueError, match='regular_file_required'):
        sources.validate(root, target, plan)


def test_final_asset_consumer_binds_all_image_records_to_captured_source_bytes(fixture, assets):  # noqa: F811
    root, original, inputs, delivery, source_plan = fixture
    _, packet, directory, manifest = assets
    packet.update(source_revision=source_plan["source_revision"],
                  source_delivery=source_plan["source_delivery"])
    manifest["source_revision"] = packet["source_revision"]
    value = sources.build(root, original, inputs, delivery, packet)
    for name in publication.source_assets(delivery, packet):
        sources.copy_file(delivery / name, directory / name)
    for image in manifest["images"].values():
        image["source_bundle"] = sources.bundle_record(value, packet)
    seal(directory, manifest)
    assert publication.checked_assets(directory, packet, root=root) == manifest
    first_part = directory / value["parts"][0]["name"]
    original_part = first_part.read_bytes()
    with publication.snapshot_assets(directory, root, packet) as captured:
        first_part.write_bytes(b"changed after capture")
        assert publication.checked_assets(captured, packet, root=root) == manifest
    assert not captured.exists()
    first_part.write_bytes(original_part)
    manifest["images"]["aikey"]["source_bundle"]["archive_sha256"] = "0" * 64
    seal(directory, manifest)
    with pytest.raises(ValueError, match="image_manifest_refused"):
        publication.checked_assets(directory, packet, root=root)


def test_part_growth_during_captured_descriptor_read_is_bounded_before_write(fixture, monkeypatch):
    root, original, inputs, target, plan = fixture
    value = sources.build(root, original, inputs, target, plan)
    part = target / value["parts"][0]["name"]
    real_open = sources.checked_file
    visits = 0
    reads = 0

    class GrowingReader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return self.stream.__exit__(*args)
        def read(self, size):
            nonlocal reads
            reads += 1
            if reads == 1:
                with part.open("ab") as writer:
                    writer.write(b"FICTIONAL growth after fstat")
            return self.stream.read(size)

    def raced_open(path, limit=sources.TOTAL_LIMIT):
        nonlocal visits
        stream = real_open(path, limit)
        if Path(path) == part:
            visits += 1
            if visits == 2:
                return GrowingReader(stream)
        return stream

    monkeypatch.setattr(sources, "checked_file", raced_open)
    with pytest.raises(ValueError, match="part_growth_refused"):
        sources.validate(root, target, plan)
    assert reads == 1  # Refuse the first oversized chunk, never drain a growing input.


@pytest.mark.parametrize("kind", [tarfile.XHDTYPE, tarfile.XGLTYPE,
                                  tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK])
def test_control_header_size_is_rejected_before_tarfile_reads_payload(fixture, monkeypatch, kind):
    root, _, _, target, plan = fixture
    target.mkdir()
    header = tarfile.TarInfo("sources/control")
    header.type, header.size = kind, 2 * sources.TOTAL_LIMIT
    raw = header.tobuf(format=tarfile.GNU_FORMAT) + bytes(1024)
    name = sources.NAME + ".part001"
    (target / name).write_bytes(raw)
    info = sources.file_info(target / name)
    value = {"schema": sources.SCHEMA, "revision": plan["source_revision"],
             "manifest_sha256": plan["source_delivery"]["manifest_sha256"],
             "sha256": info["sha256"], "parts": [dict(name=name, **info)]}
    (target / "source-bundle.json").write_text(json.dumps(value, indent=2) + "\n")
    def parser_must_not_run(*args, **kwargs):
        raise AssertionError("tarfile parser reached before raw-header refusal")
    monkeypatch.setattr(sources.tarfile, "open", parser_must_not_run)
    with pytest.raises(ValueError, match="tar_member_refused"):
        sources.validate(root, target, plan)


@pytest.mark.parametrize("fault", ["large_control", "nested_control", "sparse", "duplicate_pax",
                                   "bad_length", "negative_size", "trailing", "missing_end"])
def test_raw_tar_controls_are_bounded_and_canonical(tmp_path, fault):
    import io
    stream = io.BytesIO()
    info = tarfile.TarInfo("sources/safe")
    info.size = 1
    if fault == "sparse":
        info.pax_headers = {"GNU.sparse.size": str(2 * sources.TOTAL_LIMIT)}
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
        archive.addfile(info, io.BytesIO(b"x"))
    raw = stream.getvalue()
    if fault in ("large_control", "nested_control", "duplicate_pax", "bad_length"):
        payload = {"large_control": b"x" * (sources.PAX_LIMIT + 1),
                   "nested_control": b"13 path=safe1\n",
                   "duplicate_pax": b"13 path=safe1\n13 path=safe1\n",
                   "bad_length": b"999 path=safe\n"}[fault]
        extension = tarfile.TarInfo("././@PaxHeader")
        extension.type, extension.size = tarfile.XHDTYPE, len(payload)
        control = extension.tobuf(format=tarfile.USTAR_FORMAT)
        control += payload + bytes((-len(payload)) % 512)
        raw = control + (control if fault == "nested_control" else b"") + raw
    elif fault == "negative_size":
        info.size = -1
        raw = info.tobuf(format=tarfile.GNU_FORMAT) + bytes(1024)
    elif fault == "trailing":
        raw += b"canary" + bytes(506)
    else:
        raw = raw[:1024]
    path = tmp_path / "malformed.tar"
    path.write_bytes(raw)
    with pytest.raises((ValueError, tarfile.TarError), match="refused|header"):
        sources.preflight_tar(path)


def test_bounded_pax_long_paths_from_real_producer_remain_supported(tmp_path):
    import io
    path = tmp_path / "long.tar"
    name = "sources/" + "/".join(["long-name" * 6] * 8)
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo(name)
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    sources.preflight_tar(path)
    with tarfile.open(path, "r:") as archive:
        assert archive.getnames() == [name]
