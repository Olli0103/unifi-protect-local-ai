"""No live credentials or transport; diagnostics must never authorize publication."""
import importlib.util
import io
import json
from pathlib import Path
import urllib.error

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_diagnostic", ROOT / "tools/release_package_diagnostic.py")
diag = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diag)
CANARY = "FICTIONAL_DIAGNOSTIC_TOKEN_CANARY"


@pytest.mark.parametrize("fault", [
    "none", "default_empty", "private_http", "no_scope_header", "scope_missing",
    "owner_name", "owner_id", "owner_bool", "owner_bot", "owner_http", "next_page",
    "list_malformed", "package_malformed", "reflected_secret",
])
def test_fixed_owner_only_diagnosis_reports_counts_not_private_payload(tmp_path, fault):
    calls = []
    def read(route, token):
        calls.append(route)
        assert token == CANARY and route in diag.ROUTES.values()
        flags = {"status": 200, "has_next": fault == "next_page",
                 "scopes_header_present": fault != "no_scope_header",
                 "read_packages_scope": None if fault == "no_scope_header" else fault != "scope_missing"}
        if route == "/user":
            value = {"login": diag.OWNER, "id": diag.OWNER_ID, "type": "User"}
            if fault == "owner_name":
                value["login"] = CANARY
            elif fault == "owner_id":
                value["id"] = 1
            elif fault == "owner_bool":
                value["id"] = True
            elif fault == "owner_bot":
                value["type"] = "Bot"
            elif fault == "owner_http":
                flags["status"] = 403
            return flags, value
        package = {"name": diag.PACKAGE, "package_type": "container", "visibility": "private",
                   "repository": {"full_name": diag.REPOSITORY}, "untrusted": CANARY}
        if route == diag.ROUTES["package"]:
            if fault == "package_malformed":
                return flags, [CANARY]
            if fault == "reflected_secret":
                package.update(name=CANARY, package_type=CANARY, visibility=CANARY,
                               repository={"full_name": CANARY})
            return flags, package
        if route == diag.ROUTES["versions"]:
            return flags, [{"id": 1573317107, "untrusted": CANARY}]
        if route == diag.ROUTES["owner_default"] and fault == "default_empty":
            return flags, []
        if route == diag.ROUTES["owner_private"] and fault == "private_http":
            return dict(flags, status=403, error="http_refused"), None
        return flags, {"untrusted": CANARY} if fault == "list_malformed" else [package]
    report = diag.diagnose(CANARY, read=read)
    assert CANARY not in json.dumps(report)
    assert report["mutated"] is False and report["release_ready"] is False
    assert not list(tmp_path.iterdir())
    if fault.startswith("owner_"):
        assert not report["owner_verified"] and len(calls) == 1
    else:
        assert report["owner_verified"] and calls == list(diag.ROUTES.values())
    if fault == "default_empty":
        assert report["requests"]["owner_default"]["target_matches"] == 0
        assert report["requests"]["owner_private"]["target_matches"] == 1
    if fault == "scope_missing":
        assert report["requests"]["owner"]["read_packages_scope"] is False


@pytest.mark.parametrize("token", ["", "bad token", "bad\ntoken", "x" * 4097])
def test_invalid_token_never_starts_any_transport(token):
    report = diag.diagnose(token, read=lambda *a: pytest.fail("unexpected transport"))
    assert report["error"] == "package_read_token_required" and report["requests"] == {}


@pytest.mark.parametrize("fault", [
    "none", "oversize", "invalid_json", "invalid_utf8", "duplicate_key",
    "redirect", "http_error", "unavailable",
])
def test_exact_get_preserves_trust_and_bounds_outputs(monkeypatch, fault, capsys):
    calls = []
    raw = (b"x" * (diag.LIMIT + 1) if fault == "oversize" else b"{" if fault == "invalid_json"
           else b"\xff" if fault == "invalid_utf8" else b'{"id":1,"id":2}'
           if fault == "duplicate_key" else b'{"id":51629451}')
    class Response(io.BytesIO):
        status = 200
        headers = {"X-OAuth-Scopes": "repo, read:packages", "Link": ""}
        def read(self, count=-1):
            assert count == diag.LIMIT + 1
            return super().read(count)
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert timeout == 20 and request.method == "GET"
            assert request.full_url == "https://api.github.com/user"
            assert request.get_header("Authorization") == "Bearer " + CANARY
            if fault in {"redirect", "http_error"}:
                raise urllib.error.HTTPError(request.full_url, 307 if fault == "redirect" else 403,
                                             CANARY, {"X-OAuth-Scopes": ""}, io.BytesIO(CANARY.encode()))
            if fault == "unavailable":
                raise urllib.error.URLError(CANARY)
            return Response(raw)
    def build(*handlers):
        assert len(handlers) == 1 and isinstance(handlers[0], diag.NoRedirect)
        assert handlers[0].redirect_request(None, None, 302, "", {}, "https://example.invalid") is None
        return Opener()
    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.example.invalid")
    monkeypatch.setattr(diag.urllib.request, "build_opener", build)
    flags, data = diag.fetch("/user", CANARY)
    assert len(calls) == 1 and CANARY not in json.dumps(flags)
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err
    assert diag.os.environ["HTTPS_PROXY"] == "https://proxy.example.invalid"
    if fault == "none":
        assert data == {"id": 51629451} and flags["read_packages_scope"]
    else:
        assert data is None and flags.get("error")


def test_nonallowlisted_transport_never_receives_credential(monkeypatch):
    monkeypatch.setattr(diag.urllib.request, "build_opener", lambda *a: pytest.fail("opener"))
    flags, data = diag.fetch("https://example.invalid", CANARY)
    assert data is None and flags["error"] == "route_refused"


def test_cli_missing_secret_never_falls_back_to_workflow_token(monkeypatch, capsys):
    monkeypatch.delenv("RELEASE_PACKAGES_READ_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", CANARY)
    monkeypatch.setattr(diag.urllib.request, "build_opener", lambda *a: pytest.fail("opener"))
    assert diag.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["error"] == "package_read_token_required" and not report["owner_verified"]


def test_diagnostic_workflow_cannot_reach_staging_or_registry_writes():
    doc = yaml.load((ROOT / ".github/workflows/package-metadata-diagnostic.yml").read_text(),
                    Loader=yaml.BaseLoader)
    assert doc["on"] == {"workflow_dispatch": ""}
    assert doc["permissions"] == {"contents": "read"}
    assert set(doc["jobs"]) == {"diagnose"}
    job = doc["jobs"]["diagnose"]
    assert "environment" not in job and job["timeout-minutes"] == "5"
    assert all(x in job["if"] for x in (
        "github.ref == 'refs/heads/main'", "github.actor == 'Olli0103'",
        "github.triggering_actor == 'Olli0103'", "github.run_attempt == 1"))
    steps = job["steps"]
    assert len(steps) == 3 and steps[0]["with"]["persist-credentials"] == "false"
    assert steps[0]["with"]["ref"] == "${{ github.sha }}"
    assert steps[-1]["run"] == "python tools/release_package_diagnostic.py"
    assert steps[-1]["env"] == {
        "RELEASE_PACKAGES_READ_TOKEN": "${{ secrets.RELEASE_PACKAGES_READ_TOKEN }}"}
    assert all("uses" not in step or len(step["uses"].rsplit("@", 1)[-1]) == 40 for step in steps)
