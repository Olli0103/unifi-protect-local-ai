"""Least privilege for untrusted CI; explicit owner-only release capability graph.

This is a structural regression guard, not a human approval or proof of live
GitHub protection rules. The release preparation gate checks those separately.
"""

from copy import deepcopy
from pathlib import Path
import re
import os
import subprocess

import pytest
import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/security.yml"
WORKFLOWS = sorted(WORKFLOW.parent.glob("*.yml"))
PUBLISHER = WORKFLOW.parent / "publish-release.yml"
OWNER_DISPATCH = (
    "github.repository == 'Olli0103/unifi-protect-local-ai' && "
    "github.ref == 'refs/heads/main' && github.actor == 'Olli0103' && "
    "github.triggering_actor == 'Olli0103' && github.run_attempt == 1"
)


def workflow_policy(value, *, publisher=False):
    assert value["permissions"] == {"contents": "read"}
    jobs = value["jobs"]
    assert isinstance(jobs, dict) and jobs
    if not publisher:
        for job in jobs.values():
            permissions = job.get("permissions", {})
            assert isinstance(permissions, dict)
            assert all(scope in ("read", "none") for scope in permissions.values())
        return
    triggers = value["on"]
    assert set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"tag", "publish", "profile", "recovery_run", "recovery_release_id", "recovery_preflight_run"}
    for name in ("recovery_run", "recovery_release_id", "recovery_preflight_run"):
        assert inputs[name]["type"] == "string" and inputs[name]["default"] == ""
    assert value["defaults"] == {"run": {"working-directory": "source"}}
    assert value["env"] == {
        "RELEASE_RECOVERY_RUN": "${{ inputs.recovery_run }}",
        "RELEASE_RECOVERY_ID": "${{ inputs.recovery_release_id }}",
        "RELEASE_RECOVERY_PREFLIGHT_RUN": "${{ inputs.recovery_preflight_run }}",
    }
    assert inputs["profile"] == {
        "description": "Artifact scope; package publishes wheel and sdist only",
        "type": "choice", "options": ["package", "image"], "default": "package", "required": True,
    }
    assert inputs["publish"]["type"] == "boolean" and inputs["publish"]["default"] is False
    assert inputs["tag"]["type"] == "string" and inputs["tag"]["required"] is True
    assert value["concurrency"] == {"group": "owner-gated-release", "cancel-in-progress": False}
    expected = {
        "qualify": ({"contents": "read", "actions": "read"}, None, None),
        "reserve": ({"contents": "write", "actions": "read"}, "qualify", "release-stage"),
        "sources": ({"contents": "read", "actions": "read"}, "reserve", None),
        "packages": (
            {"contents": "read", "actions": "read", "id-token": "write", "attestations": "write"},
            ["reserve", "sources"],
            None,
        ),
        "images": (
            {
                "contents": "write",
                "actions": "read",
                "packages": "write",
                "id-token": "write",
                "attestations": "write",
            },
            ["reserve", "sources"],
            None,
        ),
        "assemble": (
            {
                "contents": "write",
                "actions": "read",
                "packages": "write",
                "id-token": "write",
                "attestations": "write",
            },
            ["reserve", "packages", "images"],
            None,
        ),
        "publish": (
            {"contents": "write", "actions": "read", "packages": "read"},
            ["reserve", "assemble"],
            "release",
        ),
    }
    assert set(jobs) == set(expected)
    assert " ".join(jobs["qualify"]["if"].split()) == OWNER_DISPATCH
    assert jobs["reserve"]["if"] == "inputs.publish"
    for name, job in jobs.items():
        permissions, needs, environment = expected[name]
        assert job["permissions"] == permissions
        assert job.get("needs") == needs and job.get("environment") == environment
        assert "uses" not in job and "concurrency" not in job
        if name in ("images", "sources"):
            assert job["if"] == "inputs.profile == 'image'"
        elif name == "packages":
            assert " ".join(job["if"].split()) == (
                "always() && needs.reserve.result == 'success' "
                "&& ((inputs.profile == 'package' && needs.sources.result == 'skipped') "
                "|| (inputs.profile == 'image' && needs.sources.result == 'success'))"
            )
        elif name == "assemble":
            assert " ".join(job["if"].split()) == (
                "always() && needs.reserve.result == 'success' && needs.packages.result == 'success' "
                "&& ((inputs.profile == 'package' && needs.images.result == 'skipped') "
                "|| (inputs.profile == 'image' && needs.images.result == 'success'))"
            )
        elif name not in ("qualify", "reserve"):
            assert job.get("if") is None
        if name == "images":
            assert job["runs-on"] == "${{ matrix.runner }}"
            assert job["strategy"]["matrix"] == {
                "include": [
                    {"arch": "amd64", "runner": "ubuntu-24.04"},
                    {"arch": "arm64", "runner": "ubuntu-24.04-arm"},
                ]
            }
        else:
            assert job["runs-on"] == "ubuntu-24.04"
        if name in ("images", "assemble"):
            assert "GH_TOKEN" not in job["env"]
        else:
            assert job["env"]["GH_TOKEN"] == "${{ github.token }}"
        assert job["env"]["RELEASE_TAG"] == "${{ inputs.tag }}"
        assert job["env"]["RELEASE_PROFILE"] == "${{ inputs.profile }}"
        assert "SOURCE_DELIVERY_DIR" not in job["env"]
        steps = job["steps"]
        # Check the ordered pre-effect prefix, not merely the presence of gates.
        assert steps[0]["uses"].startswith("actions/checkout@")
        assert steps[0]["with"] == {
            "ref": "${{ github.sha }}", "fetch-depth": 0,
            "persist-credentials": False, "path": "policy",
        }
        source_index = 3 if name == "qualify" else 1
        source = steps[source_index]
        assert source["uses"].startswith("actions/checkout@")
        source_ref = (
            "${{ steps.source.outputs.source_revision }}" if name == "qualify" else
            "${{ needs.qualify.outputs.source_revision }}" if name == "reserve" else
            "${{ needs.reserve.outputs.source_revision }}"
        )
        assert source["with"] == {
            "ref": source_ref, "fetch-depth": 0,
            "persist-credentials": False, "path": "source",
        }
        assert steps[1 if name == "qualify" else 2]["uses"].startswith("actions/setup-python@")
        if name == "qualify":
            assert steps[2] == {
                "name": "Resolve unchanged source or explicit original-run recovery",
                "id": "source", "working-directory": "policy", "shell": "bash",
                "run": "set -euo pipefail\numask 077\npython tools/release_recovery.py resolve\n",
            }
            assert job["outputs"]["source_revision"] == "${{ steps.source.outputs.source_revision }}"
        init_index = 4 if name == "qualify" else 3
        assert steps[init_index] == {
            "name": "Set runner-local source delivery path",
            "shell": "bash",
            "run": (
                "set -euo pipefail\numask 077\n"
                "printf 'SOURCE_DELIVERY_DIR=%s/source-delivery\\n' "
                '"${RUNNER_TEMP}" >> "${GITHUB_ENV}"\n'
            ),
        }
        if name != "qualify":
            preparation = steps[init_index + 1]
            assert preparation["id"] == "preparation"
            assert (
                'python "${GITHUB_WORKSPACE}/policy/tools/release_prepare.py" '
                '--root "${GITHUB_WORKSPACE}/source" --tag "${RELEASE_TAG}" --publish'
                in preparation["run"]
            )
            assert preparation.get("if") is None
        else:
            assert steps[init_index + 1]["name"] == "Read-only readiness; publishing is opt-in"
        for step in steps:
            if "uses" in step:
                assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
            if "run" in step:
                assert step["run"].startswith("set -euo pipefail\numask 077\n")
                assert "${{ inputs." not in step["run"]
            image_only = step.get("name") in {
                "Maintained native Docker Buildx", "Short-lived workflow registry login",
                "Download this run's validated source bundle before any image or asset upload",
                "aikey multiarch provenance", "aiport multiarch provenance",
                "Retain standard bundle ${{ runner.temp }}/release-candidate/aikey-index-provenance.sigstore.json",
                "Retain standard bundle ${{ runner.temp }}/release-candidate/aiport-index-provenance.sigstore.json",
            }
            if image_only:
                assert step.get("if") == "inputs.profile == 'image'"
            elif name == "reserve" and step.get("name") == "Retain release-reservation":
                assert step.get("if") == (
                    "${{ !cancelled() && (steps.reserve.outcome == 'success' || "
                    "steps.reserve.outcome == 'failure') }}"
                )
                assert step["with"]["path"] == "${{ runner.temp }}/release-reservation.json"
            elif "if" in step:
                assert name == "images" and step["if"] == "always()"
                assert step.get("run") == (
                    'set -euo pipefail\numask 077\nbash "${GITHUB_WORKSPACE}/policy/tools/container_install_run.sh" cleanup\n'
                )
            if step.get("uses", "").startswith("actions/attest@"):
                assert name in ("packages", "images", "assemble")
                assert step["with"]["create-storage-record"] is False
                assert step["with"]["push-to-registry"] is False


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_security_workflow_pins_actions_and_uses_read_only_permissions(path):
    workflow = path.read_text()
    assert "permissions:\n  contents: read" in workflow
    assert "pull_request_target" not in workflow
    assert "persist-credentials: false" in workflow
    actions = re.findall(r"uses: ([^\s#]+)", workflow)
    assert actions and all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions)
    workflow_policy(yaml.safe_load(workflow), publisher=path == PUBLISHER)


@pytest.mark.parametrize(
    "fault",
    [
        "pr_trigger",
        "implicit_publish",
        "global_write",
        "qualify_write",
        "missing_owner",
        "owner_bypass",
        "skip_stage",
        "dynamic_stage",
        "skip_candidate",
        "final_signer",
        "extra_writer",
        "unexpected_permission",
        "wrong_source_checkout",
        "persist_credentials",
        "pre_gate_upload",
        "skip_gate",
        "always_publish",
        "unpinned_action",
        "direct_input_shell",
        "untrusted_runner",
        "unconditional_upload",
        "cancel_previous", "unknown_profile", "implicit_image", "image_profile_bypass",
        "assembly_failure_bypass", "registry_profile_bypass", "skip_sources", "source_gate_bypass",
        "job_runner_context", "skip_path_init", "wrong_source_path", "conditional_path_init",
    ],
)
def test_publisher_exception_refuses_authorization_graph_and_privilege_regressions(fault):
    value = deepcopy(yaml.safe_load(PUBLISHER.read_text()))
    jobs = value["jobs"]
    if fault == "job_runner_context":
        jobs["images"]["env"]["SOURCE_DELIVERY_DIR"] = "${{ runner.temp }}/source-delivery"
    elif fault == "skip_path_init":
        jobs["images"]["steps"].pop(3)
    elif fault == "wrong_source_path":
        jobs["images"]["steps"][3]["run"] = "set -euo pipefail\numask 077\necho wrong-path\n"
    elif fault == "conditional_path_init":
        jobs["images"]["steps"][3]["if"] = "inputs.publish"
    elif fault == "skip_sources":
        jobs["images"]["needs"] = ["reserve"]
    elif fault == "source_gate_bypass":
        jobs["sources"]["steps"][4]["if"] = "false"
    elif fault == "unknown_profile":
        value["on"]["workflow_dispatch"]["inputs"]["profile"]["options"].append("unsafe")
    elif fault == "implicit_image":
        value["on"]["workflow_dispatch"]["inputs"]["profile"]["default"] = "image"
    elif fault == "image_profile_bypass":
        jobs["images"].pop("if")
    elif fault == "assembly_failure_bypass":
        jobs["assemble"]["if"] = "always()"
    elif fault == "registry_profile_bypass":
        next(step for step in jobs["publish"]["steps"]
             if step["name"] == "Short-lived workflow registry login").pop("if")
    elif fault == "pr_trigger":
        value["on"]["pull_request"] = None
    elif fault == "implicit_publish":
        value["on"]["workflow_dispatch"]["inputs"]["publish"]["default"] = True
    elif fault == "global_write":
        value["permissions"]["contents"] = "write"
    elif fault == "qualify_write":
        jobs["qualify"]["permissions"]["packages"] = "write"
    elif fault == "missing_owner":
        jobs["qualify"].pop("if")
    elif fault == "owner_bypass":
        jobs["qualify"]["if"] += " || true"
    elif fault == "skip_stage":
        jobs["images"]["needs"] = "qualify"
    elif fault == "dynamic_stage":
        jobs["reserve"]["environment"] = "${{ inputs.tag }}"
    elif fault == "skip_candidate":
        jobs["publish"]["needs"] = ["reserve", "images"]
    elif fault == "final_signer":
        jobs["publish"]["permissions"]["id-token"] = "write"
    elif fault == "extra_writer":
        jobs["other"] = deepcopy(jobs["publish"])
    elif fault == "unexpected_permission":
        jobs["images"]["permissions"]["security-events"] = "write"
    elif fault == "wrong_source_checkout":
        jobs["images"]["steps"][0]["with"]["ref"] = "${{ inputs.tag }}"
    elif fault == "persist_credentials":
        jobs["images"]["steps"][0]["with"]["persist-credentials"] = True
    elif fault == "pre_gate_upload":
        jobs["images"]["steps"].insert(2, deepcopy(jobs["images"]["steps"][-1]))
    elif fault == "skip_gate":
        jobs["images"]["steps"][4]["if"] = "false"
    elif fault == "always_publish":
        jobs["publish"]["if"] = "always()"
    elif fault == "unpinned_action":
        jobs["images"]["steps"][0]["uses"] = "actions/checkout@main"
    elif fault == "direct_input_shell":
        jobs["images"]["steps"][4]["run"] += 'echo "${{ inputs.tag }}"\n'
    elif fault == "untrusted_runner":
        jobs["images"]["strategy"]["matrix"]["include"][0]["runner"] = "self-hosted"
    elif fault == "unconditional_upload":
        jobs["images"]["steps"][-1]["if"] = "always()"
    else:
        value["concurrency"]["cancel-in-progress"] = True
    with pytest.raises((AssertionError, KeyError)):
        workflow_policy(value, publisher=True)


def test_ordinary_pull_request_ci_never_gets_a_publisher_permission_exception():
    value = yaml.safe_load(WORKFLOW.read_text())
    value["jobs"]["test-and-build"]["permissions"] = {"attestations": "write"}
    with pytest.raises(AssertionError):
        workflow_policy(value)


def test_security_workflow_keeps_required_release_gates():
    workflow = WORKFLOW.read_text()
    for required in (
        "python -m pytest -q",
        "python -m ruff check .",
        "python -m build",
        "pip-audit==2.10.1",
        "cyclonedx-bom==7.4.0",
        "python -m pip_audit",
        "python -m venv .runtime-sbom",
        "cyclonedx_py environment .runtime-sbom",
        "--no-deps -r requirements-runtime.lock",
        ".runtime-sbom/bin/python -m pip check",
        "sbom.cdx.json",
        "fetch-depth: 0",
        "GITLEAKS_VERSION: 8.30.1",
        "GITLEAKS_ARCHIVE_SHA256:",
        "sha256sum --check --strict",
        'gitleaks" git --redact --no-banner --exit-code 1 .',
    ):
        assert required in workflow
    assert "GITHUB_TOKEN" not in workflow
    assert "gitleaks/gitleaks-action" not in workflow


@pytest.mark.parametrize("job_name", yaml.safe_load(PUBLISHER.read_text())["jobs"])
def test_source_delivery_environment_reaches_later_steps(job_name, tmp_path):
    job = yaml.safe_load(PUBLISHER.read_text())["jobs"][job_name]
    runner_temp = tmp_path / "runner temp with spaces"
    runner_temp.mkdir()
    command_file = tmp_path / "github env"
    command_file.write_text("EXISTING=preserved\n")
    env = {"PATH": os.defpath, "RUNNER_TEMP": str(runner_temp), "GITHUB_ENV": str(command_file)}
    initializers = [step for step in job["steps"]
                    if step.get("name") == "Set runner-local source delivery path"]
    assert len(initializers) == 1 and "if" not in initializers[0]
    subprocess.run(["bash", "-c", initializers[0]["run"]], env=env, check=True)
    # The runner loads GITHUB_ENV for subsequent steps, not for the writing step.
    downstream = dict(line.split("=", 1) for line in command_file.read_text().splitlines())
    assert downstream == {
        "EXISTING": "preserved",
        "SOURCE_DELIVERY_DIR": str(runner_temp / "source-delivery"),
    }
    subprocess.run(
        ["bash", "-eu", "-c", 'test "${SOURCE_DELIVERY_DIR}" = "${RUNNER_TEMP}/source-delivery"'],
        env={**env, **downstream}, check=True,
    )


def test_workflow_validation_is_required_in_existing_test_and_build_job():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    job = workflow["jobs"]["test-and-build"]
    steps = job["steps"]
    install = next(s for s in steps if s["name"] == "Install checksum-pinned GitHub Actions validator")
    lint = next(s for s in steps if s["name"] == "Validate every GitHub Actions workflow")
    assert install["env"]["ACTIONLINT_ARCHIVE_SHA256"] == (
        "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
    )
    assert "actionlint_1.7.12_linux_amd64.tar.gz" in install["run"]
    assert "sha256sum --check --strict" in install["run"]
    assert install["run"].index("sha256sum --check --strict") < install["run"].index("tar --extract")
    assert lint["run"] == '"${RUNNER_TEMP}/actionlint" -shellcheck= -pyflakes='
    assert steps.index(install) < steps.index(lint) < steps.index(next(s for s in steps if s["name"] == "Run tests"))
    for step in (install, lint):
        assert "if" not in step and "continue-on-error" not in step
    assert "if" not in job and "continue-on-error" not in job
    assert "job.services.postgres.ports['5432']" in next(
        s for s in steps if s["name"] == "Run tests"
    )["env"]["AIKEY_TEST_PG_DSN"]


def test_draft_readers_have_required_visibility_but_native_shells_have_no_token():
    """GitHub draft listings require push; native builds must not receive GH_TOKEN."""
    workflow = yaml.safe_load(PUBLISHER.read_text())
    for name in ('images', 'assemble'):
        job = workflow['jobs'][name]
        assert job['permissions']['contents'] == 'write'
        assert 'GH_TOKEN' not in job['env']
        for step in job['steps']:
            if 'run' not in step:
                continue
            needs_api = ('/policy/tools/release_prepare.py' in step['run'] or
                         '/policy/tools/release_candidate.py' in step['run'])
            assert ('GH_TOKEN' in step.get('env', {})) is needs_api
            if needs_api:
                assert step['env']['GH_TOKEN'] == '${{ github.token }}'
        assert all(s['with']['persist-credentials'] is False for s in job['steps']
                   if s.get('uses', '').startswith('actions/checkout@'))
    assert workflow['jobs']['reserve']['environment'] == 'release-stage'
    assert workflow['jobs']['publish']['environment'] == 'release'
