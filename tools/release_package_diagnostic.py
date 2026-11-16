"""Bounded owner-only metadata diagnosis; never prepare or publish a release."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

HOST = "https://api.github.com"
OWNER = "Olli0103"
OWNER_ID = 51629451
PACKAGE = "local-aikey-0.1.0a1"
REPOSITORY = OWNER + "/unifi-protect-local-ai"
ROUTES = {
    "owner": "/user",
    "owner_default": "/user/packages?package_type=container&per_page=100",
    "owner_private": "/user/packages?package_type=container&visibility=private&per_page=100",
    "named_default": "/users/Olli0103/packages?package_type=container&per_page=100",
    "package": "/user/packages/container/local-aikey-0.1.0a1",
    "versions": "/user/packages/container/local-aikey-0.1.0a1/versions?per_page=100",
}
LIMIT = 128 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate metadata key")
        value[key] = item
    return value


def scope_flags(headers):
    value = headers.get("X-OAuth-Scopes") if headers is not None else None
    return {
        "scopes_header_present": value is not None,
        "read_packages_scope": None if value is None else "read:packages" in {
            item.strip() for item in value.split(",")},
    }


def fetch(route, token):
    """Fixed same-host GET, default TLS/proxy trust, no redirects or retries."""
    if route not in ROUTES.values():
        return {"status": None, "error": "route_refused"}, None
    request = urllib.request.Request(
        HOST + route, method="GET",
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "aikey-package-diagnostic"},
    )
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            flags = scope_flags(response.headers)
            raw = response.read(LIMIT + 1)
            flags.update(status=status, has_next='rel="next"' in response.headers.get("Link", ""))
            if status != 200:
                return dict(flags, error="http_refused"), None
            if len(raw) > LIMIT:
                return dict(flags, error="metadata_too_large"), None
            try:
                data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
            except (UnicodeError, ValueError, RecursionError):
                return dict(flags, error="metadata_malformed"), None
            return flags, data
    except urllib.error.HTTPError as error:
        flags = scope_flags(error.headers)
        error.close()
        return dict(flags, status=error.code, error="http_refused"), None
    except (OSError, ValueError, urllib.error.URLError):
        return {"status": None, "error": "transport_unavailable"}, None


def package_flags(value):
    if not isinstance(value, dict):
        return {"shape": "malformed"}
    visibility = value.get("visibility")
    repo = value.get("repository")
    return {
        "target_name_matches": value.get("name") == PACKAGE,
        "container_type_matches": value.get("package_type") == "container",
        "visibility": visibility if isinstance(visibility, str) and visibility in {
            "private", "public", "internal"} else "unknown",
        "repository_matches": isinstance(repo, dict) and repo.get("full_name") == REPOSITORY,
    }


def diagnose(token, *, read=fetch):
    report = {"schema": "aikey-package-diagnostic/1", "mutated": False,
              "release_ready": False, "owner_verified": False, "requests": {}}
    if not token or len(token) > 4096 or any(char.isspace() for char in token):
        return dict(report, error="package_read_token_required")
    flags, owner = read(ROUTES["owner"], token)
    verified = (flags.get("status") == 200 and isinstance(owner, dict)
                and owner.get("login") == OWNER and type(owner.get("id")) is int
                and owner["id"] == OWNER_ID and owner.get("type") == "User")
    report["requests"]["owner"] = flags
    if not verified:
        return dict(report, error="package_read_owner_unverified")
    report["owner_verified"] = True
    for name, route in ROUTES.items():
        if name == "owner":
            continue
        flags, value = read(route, token)
        result = dict(flags)
        if flags.get("status") == 200 and value is not None:
            if name == "package":
                result.update(package_flags(value))
            elif not isinstance(value, list) or len(value) > 100 or not all(
                    isinstance(row, dict) for row in value):
                result["shape"] = "malformed"
            else:
                result.update(rows=len(value), complete_first_page=not flags.get("has_next", False))
                if name == "versions":
                    result["known_incident_id_present"] = any(
                        type(row.get("id")) is int and row["id"] == 1573317107 for row in value)
                else:
                    targets = [row for row in value if row.get("name") == PACKAGE]
                    result["target_matches"] = len(targets)
                    result["target"] = package_flags(targets[0]) if len(targets) == 1 else None
        report["requests"][name] = result
    return report


def main():
    report = diagnose(os.environ.get("RELEASE_PACKAGES_READ_TOKEN", ""))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["owner_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
