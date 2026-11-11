"""Offline source-archive candidate matching; never a corresponding-source clearance.

No network, filesystem extraction, package execution, publication or approval mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

from image_sbom_check import CheckError, json_file, read_license_review, require

HEX = re.compile(r"[0-9a-f]{64}")
REV = re.compile(r"[0-9a-f]{40}")


def regular(root, relative):
    require(isinstance(relative, str) and relative and
            all(p not in ("", ".", "..") for p in relative.split("/")) and
            not relative.startswith("/"), "source_path_refused")
    current = root
    for part in relative.split("/"):
        current = current / part
        require(not current.is_symlink(), "source_symlink_refused")
    require(current.is_file(), "source_file_missing")
    return current


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class SourceIndex(defaultdict):
    def __init__(self):
        super().__init__(list)
        self.digests = {}


def read_sources(root, expected_digest):
    require(HEX.fullmatch(expected_digest) is not None, "source_digest_required")
    manifest_path = regular(root, "manifest.json")
    require(file_digest(manifest_path) == expected_digest, "source_manifest_changed")
    manifest = json_file(manifest_path)
    require(manifest.get("schema") == "selected-upstream-source-delivery/1"
            and manifest.get("release_approved") is False
            and manifest.get("complete_corresponding_source") is False,
            "source_manifest_schema_refused")
    files = manifest["files"]
    require(isinstance(files, list) and 0 < len(files) <= 10000
            and len(files) == manifest["file_count"], "source_manifest_count_refused")
    paths, total, index = set(), 0, SourceIndex()
    for row in files:
        require(isinstance(row, dict) and
                set(row) == {"path", "component", "version", "upstream_url", "sha256", "size"},
                "source_row_refused")
        require(all(isinstance(row[k], str) and row[k] for k in
                    ("component", "version", "path", "sha256", "upstream_url"))
                and HEX.fullmatch(row["sha256"]) is not None
                and type(row["size"]) is int and row["size"] >= 0
                and row["path"] not in paths, "source_row_refused")
        path = regular(root, row["path"])
        require(path.stat().st_size == row["size"] and file_digest(path) == row["sha256"],
                "source_bytes_changed")
        family = row["path"].split("/")[0]
        require(family in {"debian", "python", "interpreter", "native", "rust"},
                "source_family_refused")
        name = normalized(row["component"]) if family == "python" else row["component"]
        index[family, name, row["version"]].append(row["path"])
        index.digests[row["path"]] = row["sha256"]
        paths.add(row["path"])
        total += row["size"]
    require(total == manifest["bytes"], "source_manifest_size_refused")
    return index, len(files), total


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def properties(component):
    result = {}
    for prop in component.get("properties", []):
        key = prop["name"]
        if key in {"syft:package:type", "syft:metadata:source", "syft:metadata:sourceVersion"}:
            require(key not in result, "source_package_properties_ambiguous")
            result[key] = prop["value"]
    return result



class ArchiveEvidence:
    """Read only bounded, regular source members from already hash-verified archives."""

    def __init__(self, root, index):
        self.root, self.index, self.cache = root, index, {}

    def member(self, name, version, member):
        if re.fullmatch(r"[A-Za-z0-9._+-]{1,80}", version) is None:
            return None
        paths = self.index.get(("python", name, version), [])
        if len(paths) != 1 or not paths[0].endswith(".tar.gz"):
            return None
        key = (paths[0], member)
        path = regular(self.root, paths[0])
        require(path.stat().st_size <= 64 * 1024 * 1024, "source_archive_size_refused")
        require(file_digest(path) == self.index.digests[paths[0]], "source_bytes_changed")
        if key not in self.cache:
            found = []
            with path.open("rb") as stream:
                snapshot = stream.read(64 * 1024 * 1024 + 1)
            require(len(snapshot) <= 64 * 1024 * 1024, "source_archive_size_refused")
            require(hashlib.sha256(snapshot).hexdigest() == self.index.digests[paths[0]],
                    "source_bytes_changed")
            try:
                with tarfile.open(fileobj=io.BytesIO(snapshot), mode="r:gz") as archive:
                    for number, entry in enumerate(archive):
                        require(number < 100000 and entry.offset_data + entry.size <= 128 * 1024 * 1024,
                                "source_archive_member_limit")
                        if entry.name == member:
                            require(entry.isfile() and 0 < entry.size <= 2 * 1024 * 1024,
                                    "source_archive_member_refused")
                            found.append(archive.extractfile(entry).read(entry.size + 1))
                require(len(found) <= 1, "source_archive_member_ambiguous")
            except (tarfile.TarError, EOFError):
                raise CheckError("source_archive_unreadable") from None
            require(file_digest(path) == self.index.digests[paths[0]], "source_bytes_changed")
            self.cache[key] = (paths[0], found[0]) if found else None
        return self.cache[key]


def locations(component):
    values = {}
    for prop in component.get("properties", []):
        key = prop["name"]
        if re.fullmatch(r"syft:location:[0-9]+:path", key):
            require(key not in values and isinstance(prop["value"], str),
                    "source_package_locations_ambiguous")
            values[key] = prop["value"]
    return list(values.values())


def bundled_candidate(component, components, evidence):
    """Exact observed launcher paths plus owner/version/source members, not aliases."""
    base = "/usr/local/lib/python3.12/site-packages/"
    paths = locations(component)
    if len(paths) != 1:
        return None
    path = paths[0]
    distlib_names = {"t32.exe", "t64.exe", "t64-arm.exe", "w32.exe", "w64.exe", "w64-arm.exe"}
    setuptools_names = {prefix + suffix for prefix in ("cli", "gui")
                        for suffix in (".exe", "-32.exe", "-64.exe", "-arm64.exe")}
    if (component["name"] == "Simple Launcher" and component["version"] == "1.1.0.14"
            and path.startswith(base + "pip/_vendor/distlib/")
            and path.removeprefix(base + "pip/_vendor/distlib/") in distlib_names):
        owner = "pip"
    elif (component["name"] + ".exe" in setuptools_names and component["version"] == "UNKNOWN"
          and path == base + "setuptools/" + component["name"] + ".exe"):
        owner = "setuptools"
    else:
        return None
    owners = [c for c in components if c["name"] == owner
              and properties(c).get("syft:package:type") == "python"]
    if len(owners) != 1:
        return None
    version = owners[0]["version"]
    if (not isinstance(version, str) or re.fullmatch(r"[A-Za-z0-9._+-]{1,80}", version) is None
            or base + owner + "-" + version + ".dist-info/METADATA" not in locations(owners[0])):
        return None
    dependencies = []
    if owner == "pip":
        vendor = evidence.member(owner, version, f"pip-{version}/src/pip/_vendor/vendor.txt")
        if vendor is None:
            return None
        try:
            matches = re.findall(r"^distlib==([A-Za-z0-9._+-]{1,80})$", vendor[1].decode("utf-8"), re.M)
        except UnicodeDecodeError:
            raise CheckError("source_vendor_manifest_unreadable") from None
        if len(matches) != 1:
            return None
        source, source_version = "distlib", matches[0]
        members = [f"distlib-{source_version}/PC/launcher.c",
                   f"distlib-{source_version}/PC/CLISimpleLauncher.vcxproj",
                   f"distlib-{source_version}/PC/GUISimpleLauncher.vcxproj"]
        dependencies.append(vendor[0])
    else:
        source, source_version = owner, version
        members = [f"setuptools-{version}/launcher.c", f"setuptools-{version}/tools/build_launchers.py"]
    records = [evidence.member(source, source_version, member) for member in members]
    if any(record is None for record in records):
        return None
    return dict(source=source, source_version=source_version, family="python",
                files=sorted({record[0] for record in records}),
                resolution={"kind": "bundled_source_candidate", "owner": owner,
                            "owner_version": version, "binary_location": path,
                            "source_members": members, "supporting_archives": dependencies})

def match(component, index):
    props = properties(component)
    kind = props.get("syft:package:type")
    require(kind in {"deb", "python", "binary"}, "source_package_type_refused")
    name, version = component["name"], component["version"]
    family, source, source_version = None, name, version
    if kind == "deb":
        family = "debian"
        source = props.get("syft:metadata:source", name)
        source_version = props.get("syft:metadata:sourceVersion", version)
    elif kind == "python":
        family, source = "python", normalized(name)
    elif name == "python":
        family, source = "interpreter", "cpython"
    candidates = sorted(index.get((family, source, source_version), []))
    # A Python sdist may omit bundled libraries; a name match is deliberately
    # only an archive candidate, never proof of binary/source correspondence.
    return dict(bom_ref=component.get("bom-ref"), name=name, version=version, type=kind, source=source,
                source_version=source_version, family=family, files=candidates,
                status="archive_candidate" if candidates else "needs_evidence")


def inspect_image(directory, profile, inventory, index, expected_revision, evidence):
    receipt = inventory["profiles"][profile]
    require(receipt["schema"] == "aikey-image-inventory/2"
            and receipt["profile"] == profile
            and receipt["release_approved"] is False
            and receipt["licenses_reviewed"] is False
            and receipt["conversion_verified"] is True
            and re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["image_id"]) is not None
            and all(receipt[k] == inventory[k] for k in ("revision", "architecture", "nonce")),
            "source_image_binding_refused")
    sbom_path = regular(directory, profile + "-sbom.cdx.json")
    require(file_digest(sbom_path) == receipt["sbom_sha256"], "source_sbom_changed")
    read_license_review(regular(directory, profile + "-licenses.json"), receipt)
    sbom = json_file(sbom_path)
    require(sbom["bomFormat"] == "CycloneDX", "source_sbom_format_refused")
    systems = [c for c in sbom["components"] if c.get("type") == "operating-system"]
    require(len(systems) == 1
            and systems[0]["name"] == receipt["operating_system"]["id"]
            and systems[0]["version"] == receipt["operating_system"]["version"],
            "source_os_binding_refused")
    components = [c for c in sbom["components"]
                  if c.get("type") not in {"file", "operating-system"}]
    require(len(components) == receipt["package_count"]
            and len({c["bom-ref"] for c in components}) == len(components),
            "source_package_count_refused")
    rows = []
    for component in components:
        row = match(component, index)
        if row["type"] == "binary" and row["status"] == "needs_evidence":
            candidate = bundled_candidate(component, components, evidence)
            if candidate is not None:
                row.update(candidate, status="archive_candidate")
        rows.append(row)
    return dict(profile=profile, architecture=receipt["architecture"],
                revision=receipt["revision"], image_id=receipt["image_id"],
                sbom_sha256=receipt["sbom_sha256"],
                current_revision=receipt["revision"] == expected_revision,
                counts=dict(Counter(r["status"] for r in rows)), packages=rows)


def review(source_root, expected_digest, directories, expected_revision):
    require(REV.fullmatch(expected_revision) is not None, "source_revision_required")
    index, count, size = read_sources(source_root, expected_digest)
    evidence = ArchiveEvidence(source_root, index)
    images, arches = [], set()
    for directory in directories:
        inventory = json_file(regular(directory, "image-inventory.json"))
        require(inventory["schema"] == "aikey-image-inventory-summary/2"
                and inventory["architecture"] in {"amd64", "arm64"}
                and inventory["architecture"] not in arches
                and REV.fullmatch(inventory["revision"]) is not None
                and inventory["cleanup_verified"] is True
                and inventory["install_cases_finished"] == 8
                and inventory["release_approved"] is False
                and inventory["licenses_reviewed"] is False
                and set(inventory["profiles"]) == {"aikey", "aiport"},
                "source_inventory_refused")
        arches.add(inventory["architecture"])
        for profile in ("aikey", "aiport"):
            images.append(inspect_image(directory, profile, inventory, index, expected_revision, evidence))
    require(arches == {"amd64", "arm64"}, "source_architecture_matrix_incomplete")
    current = all(i["current_revision"] for i in images)
    return dict(schema="aikey-source-inventory-review/1", expected_revision=expected_revision,
                manifest_sha256=expected_digest, source_files_verified=count,
                source_bytes_verified=size, current_revision=current, images=images,
                complete_corresponding_source=False, release_approved=False,
                limits=["Archive candidates are metadata/source-member matches, not binary reproduction.",
                        "Bundled native/build/patch correspondence requires separate evidence.",
                        "Optional profiles and database images are outside this matrix.",
                        "Input receipts require independently trusted CI artifact digests.",
                        "Exact revisions only; no implicit ancestor or tree-equivalence waiver."])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--inventory", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    try:
        result = review(args.sources, args.manifest_sha256, args.inventory, args.revision)
        print(json.dumps(result, indent=2, sort_keys=True))
        # Zero means complete current-revision candidate matching only, never
        # approval. Missing packages or stale input remain machine-visible.
        return 0 if result["current_revision"] and all(
            not image["counts"].get("needs_evidence") for image in result["images"]) else 1
    except (CheckError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"error": str(exc), "release_approved": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
