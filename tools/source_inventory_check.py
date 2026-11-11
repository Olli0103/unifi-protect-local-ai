"""Offline source-archive candidate matching; never a corresponding-source clearance.

No network, extraction, package execution, publication or approval mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

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
    paths, total, index = set(), 0, defaultdict(list)
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


def inspect_image(directory, profile, inventory, index, expected_revision):
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
    rows = [match(c, index) for c in components]
    return dict(profile=profile, architecture=receipt["architecture"],
                revision=receipt["revision"], image_id=receipt["image_id"],
                sbom_sha256=receipt["sbom_sha256"],
                current_revision=receipt["revision"] == expected_revision,
                counts=dict(Counter(r["status"] for r in rows)), packages=rows)


def review(source_root, expected_digest, directories, expected_revision):
    require(REV.fullmatch(expected_revision) is not None, "source_revision_required")
    index, count, size = read_sources(source_root, expected_digest)
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
            images.append(inspect_image(directory, profile, inventory, index, expected_revision))
    require(arches == {"amd64", "arm64"}, "source_architecture_matrix_incomplete")
    current = all(i["current_revision"] for i in images)
    return dict(schema="aikey-source-inventory-review/1", expected_revision=expected_revision,
                manifest_sha256=expected_digest, source_files_verified=count,
                source_bytes_verified=size, current_revision=current, images=images,
                complete_corresponding_source=False, release_approved=False,
                limits=["Archive candidates are name/version matches, not binary reproduction.",
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
