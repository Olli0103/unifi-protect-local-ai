"""Transfer only the owner's hash-pinned public originals to a CI artifact.

Temporary source handoff utility, not a release or an approval generator.
Never unpack or execute downloaded files.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import urllib.request

MANIFEST_SHA256 = "e97fc8ea5f02166fe9d7280c7b16dc5f3ceed911077ddb191c7e5cea7d38bdb8"
FILE_COUNT = 764
TOTAL_BYTES = 1288871052
HOSTS = frozenset({
    "codeload.github.com", "deb.debian.org", "files.pythonhosted.org",
    "github.com", "security.debian.org", "snapshot.debian.org",
    "static.crates.io", "vault.almalinux.org", "vault.centos.org", "www.python.org",
    "release-assets.githubusercontent.com", "objects.githubusercontent.com",
})


class CollectionError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise CollectionError(code)


def public_url(value):
    require(isinstance(value, str) and len(value) <= 2048, "source_url_refused")
    require(all(32 < ord(c) < 127 for c in value), "source_url_refused")
    try:
        parts = urllib.parse.urlsplit(value)
        valid = (
            parts.scheme == "https" and parts.hostname in HOSTS
            and parts.port in (None, 443)
            and parts.username is None and parts.password is None
            and not parts.fragment
        )
    except ValueError:
        valid = False
    require(valid, "source_url_refused")
    return value


class PublicRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def unique_pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result, "manifest_duplicate_key")
        result[key] = value
    return result


def validate(raw):
    require(len(raw) <= 300000, "manifest_oversized")
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, "manifest_digest_mismatch")
    manifest = json.loads(raw, object_pairs_hook=unique_pairs)
    require(isinstance(manifest, dict), "manifest_shape_refused")
    require(manifest.get("schema") == "selected-upstream-source-delivery/1",
            "manifest_schema_refused")
    files = manifest.get("files")
    require(isinstance(files, list) and len(files) == FILE_COUNT, "manifest_count_mismatch")
    require(manifest.get("file_count") == FILE_COUNT
            and manifest.get("bytes") == TOTAL_BYTES, "manifest_totals_mismatch")
    paths = set()
    for item in files:
        require(isinstance(item, dict), "source_row_refused")
        name = item.get("path")
        require(isinstance(name, str) and 0 < len(name) <= 300, "source_path_refused")
        path = PurePosixPath(name)
        require(
            not path.is_absolute() and str(path) == name
            and all(part not in {"", ".", ".."} for part in path.parts)
            and re.fullmatch(r"[A-Za-z0-9_+./@=~-]+", name) is not None
            and name != "manifest.json" and name not in paths,
            "source_path_refused",
        )
        paths.add(name)
        require(type(item.get("size")) is int and 0 < item["size"] <= 512 * 1024 * 1024,
                "source_size_refused")
        require(isinstance(item.get("sha256"), str)
                and re.fullmatch("[0-9a-f]{64}", item["sha256"]) is not None,
                "source_digest_refused")
        public_url(item.get("upstream_url"))
    require(sum(item["size"] for item in files) == TOTAL_BYTES, "source_total_mismatch")
    # Also refuse parent-file conflicts before creating any destination or network request.
    for name in paths:
        require(not any(str(parent) in paths for parent in PurePosixPath(name).parents),
                "source_parent_conflict")
    return files


def download(item, destination):
    target = destination / item["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    digest = hashlib.sha256()
    count = 0
    opener = urllib.request.build_opener(PublicRedirects())
    request = urllib.request.Request(item["upstream_url"], headers={
        "User-Agent": "approved-open-source-handoff/1",
        "Accept-Encoding": "identity",
    })
    try:
        with opener.open(request, timeout=45) as response, partial.open("xb") as output:
            require(response.status == 200, "source_response_refused")
            public_url(response.geturl())
            while True:
                chunk = response.read(min(1024 * 1024, item["size"] - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                require(count <= item["size"], "source_exceeds_approved_size")
                digest.update(chunk)
                output.write(chunk)
            require(count == item["size"] and digest.hexdigest() == item["sha256"],
                    "source_bytes_mismatch")
        # Only a completely verified file becomes an artifact member.
        require(not target.exists(), "source_destination_exists")
        partial.rename(target)
    except CollectionError:
        raise
    except Exception:
        raise CollectionError("source_transfer_failed") from None


def collect(manifest_path, destination):
    with Path(manifest_path).open("rb") as source:
        raw = source.read(300001)
    files = validate(raw)
    destination = Path(destination)
    require(not destination.exists() and not destination.is_symlink(),
            "collection_destination_exists")
    destination.mkdir(mode=0o700)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download, item, destination) for item in files]
        for completed, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed % 100 == 0:
                print(json.dumps({"verified_original_files": completed}), flush=True)
    (destination / "manifest.json").write_bytes(raw)
    rows = sorted(p.relative_to(destination).as_posix()
                  for p in destination.rglob("*") if p.is_file())
    require(rows == sorted(["manifest.json"] + [item["path"] for item in files]),
            "collection_member_mismatch")
    # Re-read the complete payload before handing it to the maintained artifact uploader.
    for item in files:
        digest = hashlib.sha256()
        count = 0
        with (destination / item["path"]).open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                count += len(chunk)
                digest.update(chunk)
        require(count == item["size"] and digest.hexdigest() == item["sha256"],
                "collection_readback_mismatch")
    return {"files": FILE_COUNT, "bytes": TOTAL_BYTES, "manifest_sha256": MANIFEST_SHA256,
            "release_published": False, "owner_approval_generated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        require(
            os.environ.get("GITHUB_REPOSITORY") == "Olli0103/unifi-protect-local-ai"
            and os.environ.get("GITHUB_ACTOR") == "Olli0103"
            and os.environ.get("GITHUB_EVENT_NAME") == "push"
            and os.environ.get("GITHUB_REF") == "refs/heads/openclaw/mild-langoustine"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted",
            "collection_owner_hosted_context_required",
        )
        print(json.dumps(collect(args.manifest, args.destination), sort_keys=True))
        return 0
    except (CollectionError, OSError, ValueError, TypeError):
        print(json.dumps({"error": "approved_source_collection_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
