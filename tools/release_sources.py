"""Offline, exact-revision source delivery. No upload, firmware access or approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

import release_prepare as gate
import source_inventory_check as inventory

SCHEMA = "aikey-source-bundle/1"
PART_LIMIT = 2 * 1024**3 - 1024**2  # Below the GitHub per-asset ceiling.
TOTAL_LIMIT = 8 * 1024**3
FILE_LIMIT = 12000
NAME = "corresponding-source.tar"
INVENTORY_FILES = ("image-inventory.json", "summary.json",
                   "aikey-sbom.cdx.json", "aiport-sbom.cdx.json",
                   "aikey-licenses.json", "aiport-licenses.json")


def require(value, code):
    gate.require(value, code)


def checked_file(path, limit=TOTAL_LIMIT):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    source = os.fdopen(fd, "rb")
    info = os.fstat(source.fileno())
    if not (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 <= info.st_size <= limit):
        source.close()
        raise gate.PreparationError("source_delivery_regular_file_required")
    return source


def file_info(path, limit=TOTAL_LIMIT):
    digest = hashlib.sha256()
    total = 0
    with checked_file(path, limit) as source:
        while raw := source.read(1024**2):
            total += len(raw)
            require(total <= limit, "source_delivery_size_limit")
            digest.update(raw)
    return {"bytes": total, "sha256": digest.hexdigest()}


def copy_file(source, destination, limit=TOTAL_LIMIT):
    digest, total = hashlib.sha256(), 0
    with checked_file(source, limit) as stream, Path(destination).open("xb") as target:
        while raw := stream.read(1024**2):
            total += len(raw)
            require(total <= limit, "source_delivery_size_limit")
            digest.update(raw)
            target.write(raw)
    return {"bytes": total, "sha256": digest.hexdigest()}


def project_archive(root, path):
    with Path(path).open("xb") as output:
        subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                       stdout=output, stderr=subprocess.DEVNULL, check=True, timeout=30)
    return file_info(path, 64 * 1024**2)["sha256"]


def archive_paths(source_root, manifest_pin):
    raw = gate.read(source_root / "manifest.json", 4 * 1024**2)
    require(hashlib.sha256(raw).hexdigest() == manifest_pin, "source_manifest_changed")
    manifest = gate.load(raw)
    rows = manifest.get("files")
    require(isinstance(rows, list) and 0 < len(rows) <= 10000
            and type(manifest.get("bytes")) is int and 0 <= manifest["bytes"] <= TOTAL_LIMIT,
            "source_delivery_manifest_limit")
    for row in rows:
        name = row.get("path") if isinstance(row, dict) else None
        require(isinstance(name, str) and 0 < len(name) <= 4096
                and len(name.split("/")) <= 32, "source_delivery_path_limit")
    inventory.read_sources(source_root, manifest_pin)
    return ["manifest.json"] + [row["path"] for row in rows]


def checked_inventory(sources, pin, directories, revision, project, project_pin):
    # Invoke the existing CLI, not a self-declared report or stale success receipt.
    argv = [sys.executable, str(Path(__file__).with_name("source_inventory_check.py")),
            "--sources", str(sources), "--manifest-sha256", pin, "--revision", revision,
            "--project-archive", str(project), "--project-archive-sha256", project_pin]
    for directory in directories:
        argv.extend(["--inventory", str(directory)])
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(argv, stdout=output, stderr=subprocess.DEVNULL,
                                check=False, timeout=120)
        require(result.returncode == 0, "source_delivery_inventory_not_zero")
        require(0 < output.tell() <= 8 * 1024**2, "source_delivery_report_limit")
        output.seek(0)
        return gate.load(output.read())


def report(root, unpacked, plan):
    pin = plan["source_delivery"]["manifest_sha256"]
    with tempfile.TemporaryDirectory(prefix="project-source-") as temporary:
        expected = project_archive(root, Path(temporary) / "expected.tar")
    require(file_info(unpacked / "project.tar", 64 * 1024**2)["sha256"] == expected,
            "source_delivery_project_bytes_mismatch")
    result = checked_inventory(unpacked / "sources", pin,
                              [unpacked / "inventories" / arch for arch in ("amd64", "arm64")],
                              plan["source_revision"], unpacked / "project.tar", expected)
    require(result["current_revision"] and len(result["images"]) == 4
            and all(not row["counts"].get("needs_evidence") for row in result["images"]),
            "source_delivery_inventory_incomplete")
    return result


def metadata(directory, plan):
    raw = gate.read(Path(directory) / "source-bundle.json")
    value = gate.load(raw)
    require(raw == (json.dumps(value, indent=2) + "\n").encode(),
            "source_delivery_metadata_encoding_refused")
    require(set(value) == {"schema", "revision", "manifest_sha256", "sha256", "parts"}
            and value["schema"] == SCHEMA and value["revision"] == plan["source_revision"]
            and value["manifest_sha256"] == plan["source_delivery"]["manifest_sha256"]
            and isinstance(value["sha256"], str) and gate.HASH.fullmatch(value["sha256"])
            and isinstance(value["parts"], list) and 1 <= len(value["parts"]) <= 8,
            "source_delivery_metadata_refused")
    total = 0
    for i, part in enumerate(value["parts"], 1):
        require(isinstance(part, dict) and set(part) == {"name", "bytes", "sha256"}
                and part["name"] == NAME + ".part" + str(i).zfill(3)
                and type(part["bytes"]) is int and 0 < part["bytes"] <= PART_LIMIT
                and isinstance(part["sha256"], str) and gate.HASH.fullmatch(part["sha256"]),
                "source_delivery_part_refused")
        total += part["bytes"]
    require(total <= TOTAL_LIMIT, "source_delivery_size_limit")
    return value


def bundle_record(value, plan):
    base = "https://github.com/" + gate.REPOSITORY + "/releases/download/" + plan["tag"] + "/"
    return {"url": base + "source-bundle.json",
            "sha256": hashlib.sha256((json.dumps(value, indent=2) + "\n").encode()).hexdigest(),
            "archive_sha256": value["sha256"],
            "parts": [{**part, "url": base + part["name"]} for part in value["parts"]]}


def validate(root, directory, plan):
    """Reconstruct only bounded regular files, then rerun the actual inventory checker."""
    directory = Path(directory)
    value = metadata(directory, plan)
    with tempfile.TemporaryDirectory(prefix="source-delivery-") as temporary:
        stage = Path(temporary)
        archive = stage / "bundle.tar"
        digest = hashlib.sha256()
        with archive.open("xb") as output:
            for part in value["parts"]:
                require(file_info(directory / part["name"], PART_LIMIT)
                        == {"bytes": part["bytes"], "sha256": part["sha256"]},
                        "source_delivery_part_bytes_mismatch")
                with checked_file(directory / part["name"], PART_LIMIT) as source:
                    while raw := source.read(1024**2):
                        digest.update(raw)
                        output.write(raw)
        require(digest.hexdigest() == value["sha256"], "source_delivery_digest_mismatch")
        unpacked = stage / "unpacked"
        unpacked.mkdir(mode=0o700)
        seen, total = set(), 0
        with tarfile.open(archive, "r:") as source:
            for item in source:
                parts = item.name.split("/")
                require(len(seen) < FILE_LIMIT and len(item.name) <= 4096
                        and len(parts) <= 32 and item.isfile()
                        and not item.name.startswith("/") and all(p not in ("", ".", "..") for p in parts)
                        and "\\" not in item.name and item.name not in seen
                        and (item.name.startswith(("sources/", "inventories/")) or item.name == "project.tar")
                        and item.size <= TOTAL_LIMIT, "source_delivery_member_refused")
                total += item.size
                require(total <= TOTAL_LIMIT, "source_delivery_size_limit")
                path = unpacked.joinpath(*PurePosixPath(item.name).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(item) as stream, path.open("xb") as target:
                    shutil.copyfileobj(stream, target, length=1024**2)
                seen.add(item.name)
        result = report(root, unpacked, plan)
        allowed = {"sources/" + p for p in archive_paths(unpacked / "sources", value["manifest_sha256"])}
        allowed |= {"inventories/" + arch + "/" + name
                    for arch in ("amd64", "arm64") for name in INVENTORY_FILES}
        require(seen == allowed | {"project.tar"}, "source_delivery_member_set_mismatch")
    return value, result


def build(root, sources, inventories, destination, plan, *, part_limit=PART_LIMIT):
    """Sources are owner-supplied originals, not fetched packages or guessed substitutes."""
    sources, destination = Path(sources), Path(destination)
    paths = archive_paths(sources, plan["source_delivery"]["manifest_sha256"])
    require(1 <= part_limit <= PART_LIMIT, "source_delivery_part_size_refused")
    destination.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix="source-build-") as temporary:
        stage = Path(temporary)
        (stage / "inventories").mkdir()
        for arch in ("amd64", "arm64"):
            target = stage / "inventories" / arch
            target.mkdir()
            for name in INVENTORY_FILES:
                copy_file(Path(inventories) / ("container-install-" + arch) / name, target / name,
                          32 * 1024**2)
        project_archive(root, stage / "project.tar")
        # review() also verifies all 764 originals and the exact four-image subject.
        pinned_project = file_info(stage / "project.tar", 64 * 1024**2)["sha256"]
        result = checked_inventory(sources, plan["source_delivery"]["manifest_sha256"],
                                  [stage / "inventories" / arch for arch in ("amd64", "arm64")],
                                  plan["source_revision"], stage / "project.tar", pinned_project)
        require(result["current_revision"] and all(not i["counts"].get("needs_evidence")
                                                   for i in result["images"]),
                "source_delivery_inventory_incomplete")
        archive = stage / "bundle.tar"
        with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as target:
            entries = [(sources / name, "sources/" + name) for name in paths]
            entries += [(stage / "project.tar", "project.tar")]
            entries += [(stage / "inventories" / arch / name, "inventories/" + arch + "/" + name)
                        for arch in ("amd64", "arm64") for name in INVENTORY_FILES]
            for path, name in entries:
                info = file_info(path)
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.mtime = info["bytes"], 0o644, plan["source_date_epoch"]
                with checked_file(path) as stream:
                    target.addfile(member, stream)
        full = file_info(archive)
        parts = []
        with checked_file(archive) as source:
            number = 1
            while raw := source.read(min(part_limit, 1024**2)):
                name = NAME + ".part" + str(number).zfill(3)
                digest, length = hashlib.sha256(), 0
                with (destination / name).open("xb") as output:
                    while raw:
                        output.write(raw)
                        digest.update(raw)
                        length += len(raw)
                        if length == part_limit:
                            break
                        raw = source.read(min(1024**2, part_limit - length))
                parts.append({"name": name, "bytes": length, "sha256": digest.hexdigest()})
                number += 1
        value = {"schema": SCHEMA, "revision": plan["source_revision"],
                 "manifest_sha256": plan["source_delivery"]["manifest_sha256"],
                 "sha256": full["sha256"], "parts": parts}
        (destination / "source-bundle.json").write_text(json.dumps(value, indent=2) + "\n")
    validate(root, destination, plan)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--inventories", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        plan = gate.prepare(root, args.tag, publish=True, profile="image")
        result = build(root, args.sources, args.inventories, args.destination, plan)
        print(json.dumps({"source_bundle": bundle_record(result, plan), "uploaded": False}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, tarfile.TarError):
        print(json.dumps({"error": "source_delivery_unavailable", "uploaded": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
