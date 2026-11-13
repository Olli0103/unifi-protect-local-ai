"""Fictional recovery records. No GitHub write, signature or real approval."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from test_release_assets import assets  # noqa: F401
from test_release_prepare import gate
from test_release_publication import publication, plan

SPEC = importlib.util.spec_from_file_location(
    "recovery_under_test", Path(__file__).resolve().parents[1] / "tools/release_recovery.py")
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


@pytest.fixture
def records(tmp_path, monkeypatch):
    policy = tmp_path / "policy"
    (policy / "tools").mkdir(parents=True)
    monkeypatch.setattr(recovery, "__file__", str(policy / "tools/release_recovery.py"))
    source = "b" * 40
    policy_sha = "a" * 40
    env = {
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REPOSITORY": gate.REPOSITORY,
        "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW_REF": gate.WORKFLOW,
        "GITHUB_ACTOR": gate.OWNER, "GITHUB_TRIGGERING_ACTOR": gate.OWNER,
        "GITHUB_SHA": policy_sha, "RUNNER_ENVIRONMENT": "github-hosted",
        "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64", "GITHUB_RUN_ID": "200",
        "GITHUB_RUN_ATTEMPT": "1", "RELEASE_RECOVERY_RUN": "123", "RELEASE_RECOVERY_ID": "99",
    }
    person = {"id": gate.OWNER_ID, "login": gate.OWNER, "type": "User"}
    original = {
        "id": 123, "event": "workflow_dispatch", "path": ".github/workflows/publish-release.yml",
        "head_branch": "main", "head_sha": source, "run_attempt": 1,
        "status": "completed", "conclusion": "failure",
        "actor": person, "triggering_actor": copy.deepcopy(person),
        "repository": {"full_name": gate.REPOSITORY},
        "created_at": "2026-01-01T01:00:00Z",
    }
    jobs = [{"id": number, "name": name, "status": "completed", "conclusion": conclusion}
            for number, (name, conclusion) in enumerate(
                [("qualify", "success"), ("reserve", "failure"), ("sources", "skipped"),
                 ("images", "skipped"), ("packages", "skipped"), ("assemble", "skipped"),
                 ("publish", "skipped")], 10)]
    state = {"original": original, "jobs": jobs, "history": [{"id": 123}, {"id": 200}],
             "dirty": "", "ci": [], "calls": []}

    def run(argv, *, cwd, **kwargs):
        state["calls"].append((argv, cwd))
        if argv == ["git", "rev-parse", "HEAD"]:
            assert cwd == policy
            return policy_sha
        if argv == ["git", "status", "--porcelain", "--untracked-files=all"]:
            return state["dirty"]
        assert argv[:2] == ["gh", "api"]
        if argv[-1].endswith("/runs/123"):
            return json.dumps(state["original"])
        if argv[-1].endswith("/runs/123/jobs?per_page=100"):
            return json.dumps({"total_count": state.get("jobs_total", len(state["jobs"])),
                               "jobs": state["jobs"]})
        assert argv[-1].endswith("/workflows/publish-release.yml/runs?event=workflow_dispatch&per_page=100")
        return json.dumps({"total_count": state.get("history_total", len(state["history"])),
                           "workflow_runs": state["history"]})

    def ci(root, revision, run):
        state["ci"].append((root, revision))
        if state.get("ci_failed"):
            raise gate.PreparationError("release_ci_jobs_not_successful")
        return [{"FICTIONAL": True}]

    monkeypatch.setattr(gate, "continuous_integration", ci)
    return policy, source, policy_sha, env, state, run


def test_empty_original_reservation_can_be_reconciled_with_distinct_policy_source(records):
    policy, source, policy_sha, env, state, run = records
    assert recovery.resolve(gate, env, run) == source
    bound = recovery.context(policy.parent / "source", source, gate, env, run, profile="image")
    assert bound == {
        "schema": "aikey-release-recovery/1", "original_run_id": "123", "reservation_id": 99,
        "source_revision": source, "workflow_revision": policy_sha,
        "workflow_run_id": "200", "profile": "image"}
    assert state["ci"] == [(policy, policy_sha)]
    assert all(argv[0] in {"git", "gh"} and
               (argv[0] != "gh" or argv[:2] == ["gh", "api"]) for argv, _ in state["calls"])


@pytest.mark.parametrize("fault", [
    "one_input", "boolean_id", "leading_zero", "shell_id", "same_run", "other_owner",
    "other_source", "other_repo", "other_workflow", "old_rerun", "running", "success",
    "qualify_failed", "image_succeeded", "image_failed", "unknown_job", "duplicate_job",
    "jobs_partial", "history_partial", "intervening", "missing_current", "missing_origin",
    "dirty_policy", "policy_ci_failed", "package_profile", "policy_sha_mismatch", "current_rerun",
])
def test_recovery_refuses_unknown_prior_effects_or_unqualified_policy(records, fault):
    policy, source, _, env, state, run = records
    profile = "image"
    if fault == "one_input":
        env["RELEASE_RECOVERY_ID"] = ""
    elif fault == "boolean_id":
        env["RELEASE_RECOVERY_ID"] = True
    elif fault == "leading_zero":
        env["RELEASE_RECOVERY_RUN"] = "0123"
    elif fault == "shell_id":
        env["RELEASE_RECOVERY_RUN"] = "123;FICTIONAL"
    elif fault == "same_run":
        env["GITHUB_RUN_ID"] = "123"
    elif fault == "other_owner":
        state["original"]["actor"]["id"] = 1
    elif fault == "other_source":
        source = "c" * 40
    elif fault == "other_repo":
        state["original"]["repository"]["full_name"] = "FICTIONAL/other"
    elif fault == "other_workflow":
        state["original"]["path"] = ".github/workflows/other.yml"
    elif fault == "old_rerun":
        state["original"]["run_attempt"] = 2
    elif fault == "running":
        state["original"]["status"] = "in_progress"
    elif fault == "success":
        state["original"]["conclusion"] = "success"
    elif fault == "qualify_failed":
        state["jobs"][0]["conclusion"] = "failure"
    elif fault == "image_succeeded":
        state["jobs"][3]["conclusion"] = "success"
    elif fault == "image_failed":
        state["jobs"][3]["conclusion"] = "failure"
    elif fault == "unknown_job":
        state["jobs"][3]["name"] = "FICTIONAL-unknown"
    elif fault == "duplicate_job":
        state["jobs"].append(copy.deepcopy(state["jobs"][0]))
    elif fault == "jobs_partial":
        state["jobs_total"] = 100
    elif fault == "history_partial":
        state["history_total"] = 1000
    elif fault == "intervening":
        state["history"].append({"id": 100, "created_at": "2026-01-01T01:00:01Z"})
    elif fault == "missing_current":
        state["history"].pop()
    elif fault == "missing_origin":
        state["history"].pop(0)
    elif fault == "dirty_policy":
        state["dirty"] = " M tools/release_prepare.py"
    elif fault == "policy_ci_failed":
        state["ci_failed"] = True
    elif fault == "package_profile":
        profile = "package"
    elif fault == "policy_sha_mismatch":
        env["GITHUB_SHA"] = "c" * 40
    elif fault == "current_rerun":
        env["GITHUB_RUN_ATTEMPT"] = "2"
    with pytest.raises(gate.PreparationError):
        recovery.context(policy.parent / "source", source, gate, env, run, profile=profile)


def test_normal_mode_still_refuses_source_workflow_mismatch(records):
    policy, source, _, env, _, run = records
    env.pop("RELEASE_RECOVERY_RUN")
    env.pop("RELEASE_RECOVERY_ID")
    with pytest.raises(gate.PreparationError, match="provenance_mismatch"):
        recovery.context(policy, source, gate, env, run, profile="image")


def recovery_plan():
    value = plan()
    value["workflow_run_id"] = "200"
    value["recovery"] = {
        "schema": "aikey-release-recovery/1", "original_run_id": "123", "reservation_id": 99,
        "source_revision": value["source_revision"], "workflow_revision": "c" * 40,
        "workflow_run_id": "200", "profile": "image",
    }
    return value


@pytest.mark.parametrize("fault", ["none", "wrong_id", "wrong_run", "wrong_source", "published",
                                    "assets", "incomplete_assets"])
def test_adopt_exact_empty_draft_performs_zero_writes(tmp_path, fault):
    packet = recovery_plan()
    draft = {"id": 99, "tag_name": packet["tag"], "draft": True,
             "target_commitish": packet["source_revision"], "body": publication.marker(packet)}
    if fault == "wrong_id":
        draft["id"] = 98
    elif fault == "wrong_run":
        draft["body"] = draft["body"].replace("run=123", "run=124")
    elif fault == "wrong_source":
        draft["target_commitish"] = "b" * 40
    elif fault == "published":
        draft["draft"] = False
    writes = []

    def run(argv, **kwargs):
        if "/releases?" in argv[-1]:
            return json.dumps([[draft]])
        assert argv[-1].endswith("/releases/99/assets?per_page=100")
        return json.dumps({} if fault == "incomplete_assets" else
                          [[{"id": 1}]] if fault == "assets" else [[]])

    def write(*args):
        writes.append(args)
        pytest.fail("draft adoption must never create/edit/delete any resource")

    if fault == "none":
        result = publication.reserve(tmp_path, packet, run=run, write=write)
        assert result["release_id"] == 99 and result["recovery"] == packet["recovery"]
        assert result["phase"] == "draft_reserved" and result["published"] is False
        assert result["write_acknowledged"] is False
    else:
        with pytest.raises(ValueError):
            publication.reserve(tmp_path, packet, run=run, write=write)
    assert writes == []


def test_recovery_signature_verifier_pins_actual_policy_not_old_source(tmp_path):
    packet = recovery_plan()
    calls = []
    publication.verify_subject(tmp_path, packet, tmp_path, "FICTIONAL-package",
                               "bundle.json", run=lambda argv, **kw: calls.append(argv))
    argv = calls[0]
    for option in ("--source-digest", "--signer-digest"):
        assert argv[argv.index(option) + 1] == packet["recovery"]["workflow_revision"]
    assert argv[argv.index("--source-ref") + 1] == "refs/heads/main"


@pytest.mark.parametrize("fault", ["none", "origin", "policy", "source", "current", "missing"])
def test_signed_manifest_must_bind_exact_recovery_context(assets, fault):  # noqa: F811 -- imported fixture
    _, packet, folder, manifest = assets
    packet["workflow_run_id"] = "200"
    manifest["workflow_run_id"] = "200"
    packet["recovery"] = recovery_plan()["recovery"]
    manifest["schema"] = "aikey-release-assets/2"
    manifest["recovery"] = copy.deepcopy(packet["recovery"])
    if fault == "origin":
        manifest["recovery"]["original_run_id"] = "124"
    elif fault == "policy":
        manifest["recovery"]["workflow_revision"] = "d" * 40
    elif fault == "source":
        manifest["recovery"]["source_revision"] = "e" * 40
    elif fault == "current":
        manifest["recovery"]["workflow_run_id"] = "201"
    elif fault == "missing":
        del manifest["recovery"]
    (folder / "release.json").write_text(json.dumps(manifest))
    if fault == "none":
        assert publication.checked_assets(folder, packet)["recovery"] == packet["recovery"]
    else:
        with pytest.raises(ValueError, match="release_assets_source_mismatch"):
            publication.checked_assets(folder, packet)


def test_workflow_keeps_policy_source_and_final_approval_separate():
    path = Path(__file__).resolve().parents[1] / ".github/workflows/publish-release.yml"
    workflow = yaml.safe_load(path.read_text())
    jobs = workflow["jobs"]
    assert jobs["publish"]["environment"] == "release"
    assert jobs["reserve"]["environment"] == "release-stage"
    assert jobs["images"]["env"]["SOURCE_REVISION"] == "${{ needs.reserve.outputs.source_revision }}"
    assert jobs["images"]["env"]["INSTALL_SOURCE_ROOT"] == "${{ github.workspace }}/source"
    assert jobs["images"]["env"]["INSTALL_TOOLS_ROOT"] == "${{ github.workspace }}/policy/tools"
    for name, job in jobs.items():
        checkouts = [step for step in job["steps"]
                     if step.get("uses", "").startswith("actions/checkout@")]
        assert [step["with"]["path"] for step in checkouts] == ["policy", "source"]
        assert checkouts[0]["with"]["ref"] == "${{ github.sha }}"
        assert all(step["with"]["persist-credentials"] is False for step in checkouts)
    steps = jobs["qualify"]["steps"]
    setup = next(i for i, step in enumerate(steps)
                 if step.get("uses", "").startswith("actions/setup-python@"))
    resolve = next(i for i, step in enumerate(steps) if step.get("id") == "source")
    assert setup < resolve


@pytest.mark.parametrize("missing", ["sources", "packages", "images", "assemble", "publish", "all"])
def test_recovery_requires_positive_proof_of_every_downstream_job(records, missing):
    policy, source, _, env, state, run = records
    state["jobs"] = [item for item in state["jobs"]
                     if item["name"] in {"qualify", "reserve"}
                     or (missing != "all" and item["name"] != missing)]
    with pytest.raises(gate.PreparationError, match="original_jobs_refused"):
        recovery.context(policy.parent / "source", source, gate, env, run, profile="image")


@pytest.mark.parametrize("fault", ["none", "only_amd64", "only_arm64", "placeholder_and_matrix"])
def test_recovery_requires_both_matrix_records_or_single_skipped_placeholder(records, fault):
    policy, source, _, env, state, run = records
    state["jobs"] = [item for item in state["jobs"] if item["name"] != "images"]
    for index, arch in enumerate(("amd64", "arm64")):
        if fault == "only_amd64" and arch == "arm64":
            continue
        if fault == "only_arm64" and arch == "amd64":
            continue
        state["jobs"].append({"id": 100 + index, "name": f"images ({arch})",
                              "status": "completed", "conclusion": "skipped"})
    if fault == "placeholder_and_matrix":
        state["jobs"].append({"id": 102, "name": "images", "status": "completed",
                              "conclusion": "skipped"})
    if fault == "none":
        assert recovery.context(policy.parent / "source", source, gate, env, run,
                                profile="image")["original_run_id"] == "123"
    else:
        with pytest.raises(gate.PreparationError, match="original_jobs_refused"):
            recovery.context(policy.parent / "source", source, gate, env, run, profile="image")


@pytest.mark.parametrize("fault", [
    "none", "rerun", "late_rerun", "missing_attempt", "boolean_attempt", "active",
    "late_completion", "same_time", "missing_start", "missing_update", "inverted_times",
])
def test_older_dispatch_must_be_closed_single_attempt_before_origin(records, fault):
    policy, source, _, env, state, run = records
    older = {"id": 99, "run_attempt": 1, "status": "completed",
             "created_at": "2025-12-31T22:00:00Z", "run_started_at": "2025-12-31T22:01:00Z",
             "updated_at": "2025-12-31T22:02:00Z"}
    if fault in ("rerun", "late_rerun"):
        older["run_attempt"] = 2
    if fault == "late_rerun":
        older.update(run_started_at="2026-01-01T02:00:00Z", updated_at="2026-01-01T02:01:00Z")
    elif fault == "missing_attempt":
        older.pop("run_attempt")
    elif fault == "boolean_attempt":
        older["run_attempt"] = True
    elif fault == "active":
        older["status"] = "in_progress"
    elif fault == "late_completion":
        older["updated_at"] = "2026-01-01T02:00:00Z"
    elif fault == "same_time":
        older["updated_at"] = state["original"]["created_at"]
    elif fault == "missing_start":
        older.pop("run_started_at")
    elif fault == "missing_update":
        older.pop("updated_at")
    elif fault == "inverted_times":
        older["run_started_at"] = "2025-12-31T21:00:00Z"
    state["history"].append(older)
    if fault == "none":
        assert recovery.context(policy.parent / "source", source, gate, env, run,
                                profile="image")["original_run_id"] == "123"
    else:
        with pytest.raises(gate.PreparationError):
            recovery.context(policy.parent / "source", source, gate, env, run, profile="image")


@pytest.fixture
def prepush_records(records):
    import hashlib
    policy, source, policy_sha, env, state, base_run = records
    env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '150'
    record = json.loads((Path(__file__).resolve().parents[1] /
                         'docs/legal/recovery-prepush-reconciliation.json').read_text())
    record.update(original_run_id='123', reservation_id=99, source_revision=source,
                  run_id='150', policy_revision='d' * 40,
                  workflow_sha256=hashlib.sha256(b'FICTIONAL reviewed workflow\n').hexdigest())
    for number, row in enumerate(record['jobs'], 100):
        row['id'] = number
    # Fictional live graph: required guard names plus unique fixture-only steps.
    live_jobs = copy.deepcopy(record['jobs'])
    effect_names = {
        13: 'Bind pre-push intent to tested image configs and inventories',
        15: 'Short-lived workflow registry login',
        16: 'Push only these attempt-specific images; observe immutable manifests',
        17: 'Remove owned local fixtures and verify zero remaining resources',
    }
    for recorded_job, live_job in zip(record['jobs'], live_jobs, strict=True):
        for recorded_step, live_step in zip(recorded_job['steps'], live_job['steps'], strict=True):
            name = (effect_names.get(live_step['number'])
                    if live_job['name'].startswith('images (') else None)
            name = name or f'FICTIONAL step {live_step["number"]}'
            live_step.pop('name_sha256')
            live_step['name'] = name
            recorded_step['name_sha256'] = hashlib.sha256(name.encode('utf-8')).hexdigest()
    state['preflight_record'] = record
    state['preflight_jobs'] = live_jobs
    previous = copy.deepcopy(state['original'])
    previous.update(id=150, head_sha='d' * 40, created_at='2026-01-01T02:00:00Z',
                    updated_at='2026-01-01T03:00:00Z')
    state['preflight_run'] = previous
    state['history'] = [{'id': 123}, copy.deepcopy(previous),
                        {'id': 200, 'created_at': '2026-01-01T04:00:00Z'}]
    folder = policy / 'docs/legal'
    folder.mkdir(parents=True)
    path = folder / 'recovery-prepush-reconciliation.json'
    path.write_text(json.dumps(record))
    state['record_path'] = path

    def run(argv, *, cwd, **kwargs):
        if argv[-1].endswith('/runs/150'):
            return json.dumps(state['preflight_run'])
        if argv[-1].endswith('/runs/150/jobs?per_page=100'):
            return json.dumps({'total_count': state.get('preflight_total', 8),
                               'jobs': state['preflight_jobs']})
        if argv[:2] == ['git', 'show']:
            assert argv[-1] == 'd' * 40 + ':.github/workflows/publish-release.yml'
            return state.get('workflow_bytes', 'FICTIONAL reviewed workflow\n')
        return base_run(argv, cwd=cwd, **kwargs)
    return policy, source, policy_sha, env, state, run


def test_exact_reviewed_pre_push_failure_can_be_reconciled_without_writes(prepush_records):
    policy, source, _, env, state, run = prepush_records
    result = recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')
    assert result['original_run_id'] == '123' and result['reservation_id'] == 99
    assert result['reconciled_preflight']['run_id'] == '150'
    assert result['reconciled_preflight']['workflow_revision'] == 'd' * 40
    assert len(result['reconciled_preflight']['jobs_sha256']) == 64
    assert state['ci'] == [(policy, 'a' * 40)]


@pytest.mark.parametrize('fault', [
    'no_opt_in', 'unknown_run', 'same_current', 'same_original', 'no_original_inputs',
    'missing_record', 'different_source', 'different_draft', 'different_origin',
    'different_policy', 'workflow_bytes', 'rerun', 'foreign_owner', 'partial_jobs',
    'missing_job', 'extra_job', 'duplicate_job', 'missing_step', 'unknown_step',
    'changed_step', 'registry_login', 'image_push', 'cleanup_failed', 'package_succeeded',
    'publish_ran', 'assemble_ran', 'intervening_other', 'prior_not_in_history',
    'prior_still_running', 'newer_current_race', 'renamed_step',
    'raw_record_name', 'bad_name_digest', 'legacy_record',
])
def test_pre_push_reconciliation_refuses_every_ambiguous_effect(prepush_records, fault):
    policy, source, _, env, state, run = prepush_records
    if fault == 'no_opt_in':
        env.pop('RELEASE_RECOVERY_PREFLIGHT_RUN')
    elif fault == 'unknown_run':
        env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '151'
    elif fault == 'same_current':
        env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '200'
    elif fault == 'same_original':
        env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '123'
    elif fault == 'no_original_inputs':
        env['RELEASE_RECOVERY_RUN'] = env['RELEASE_RECOVERY_ID'] = ''
    elif fault == 'missing_record':
        state['record_path'].unlink()
    elif fault.startswith('different_'):
        key = {'source': 'source_revision', 'draft': 'reservation_id',
               'origin': 'original_run_id', 'policy': 'policy_revision'}[fault[10:]]
        state['preflight_record'][key] = 100 if key == 'reservation_id' else 'c' * 40
        state['record_path'].write_text(json.dumps(state['preflight_record']))
    elif fault in ('raw_record_name', 'bad_name_digest', 'legacy_record'):
        record = state['preflight_record']
        if fault == 'legacy_record':
            record['schema'] = 'aikey-prepush-reconciliation/1'
        else:
            step = record['jobs'][0]['steps'][0]
            if fault == 'raw_record_name':
                step['name'] = 'FICTIONAL runner path'
            else:
                step['name_sha256'] = 'not a digest'
        state['record_path'].write_text(json.dumps(record))
    elif fault == 'renamed_step':
        state['preflight_jobs'][0]['steps'][0]['name'] += ' changed'
    elif fault == 'workflow_bytes':
        state['workflow_bytes'] = 'FICTIONAL unknown policy'
    elif fault == 'rerun':
        state['preflight_run']['run_attempt'] = 2
    elif fault == 'foreign_owner':
        state['preflight_run']['actor']['id'] = 1
    elif fault == 'partial_jobs':
        state['preflight_total'] = 100
    elif fault == 'missing_job':
        state['preflight_jobs'].pop()
    elif fault == 'extra_job':
        state['preflight_jobs'].append(copy.deepcopy(state['preflight_jobs'][0]))
    elif fault == 'duplicate_job':
        state['preflight_jobs'][1]['id'] = state['preflight_jobs'][0]['id']
    elif fault in ('missing_step', 'unknown_step', 'changed_step', 'registry_login',
                   'image_push', 'cleanup_failed'):
        row = next(row for row in state['preflight_jobs'] if row['name'].startswith('images ('))
        if fault == 'missing_step':
            row['steps'].pop()
        elif fault == 'unknown_step':
            row['steps'].append({'number': 999, 'name': 'FICTIONAL unknown step',
                                 'status': 'completed', 'conclusion': 'success'})
        else:
            name = {'changed_step': 'Bind pre-push intent to tested image configs and inventories',
                    'registry_login': 'Short-lived workflow registry login',
                    'image_push': 'Push only these attempt-specific images; observe immutable manifests',
                    'cleanup_failed': 'Remove owned local fixtures and verify zero remaining resources'}[fault]
            step = next(step for step in row['steps'] if step['name'] == name)
            step['conclusion'] = 'failure' if fault == 'cleanup_failed' else 'success'
    elif fault in ('package_succeeded', 'publish_ran', 'assemble_ran'):
        name = {'package_succeeded': 'packages', 'publish_ran': 'publish', 'assemble_ran': 'assemble'}[fault]
        next(row for row in state['preflight_jobs'] if row['name'] == name)['conclusion'] = 'success'
    elif fault == 'intervening_other':
        state['history'].append({'id': 175, 'created_at': '2026-01-01T03:30:00Z'})
    elif fault == 'prior_not_in_history':
        state['history'].pop(1)
    elif fault == 'prior_still_running':
        state['history'][1]['status'] = 'in_progress'
    elif fault == 'newer_current_race':
        state['history'][2]['created_at'] = '2026-01-01T02:30:00Z'
    with pytest.raises((gate.PreparationError, OSError, KeyError)):
        recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')


@pytest.fixture
def followup_records(prepush_records):
    """Fictional second terminal pre-registry failure; no API writes."""
    import hashlib
    policy, source, policy_sha, env, state, base_run = prepush_records
    earlier = state['preflight_run']
    current = copy.deepcopy(earlier)
    current.update(id=175, head_sha='e' * 40, created_at='2026-01-01T03:10:00Z',
                   updated_at='2026-01-01T03:20:00Z')
    record = copy.deepcopy(state['preflight_record'])
    record.update(run_id='175', policy_revision='e' * 40,
                  workflow_sha256=hashlib.sha256(b'FICTIONAL second workflow\n').hexdigest())
    jobs = copy.deepcopy(state['preflight_jobs'])
    for recorded, live in zip(record['jobs'], jobs, strict=True):
        recorded['id'] += 1000
        live['id'] += 1000
        if recorded['name'] == 'packages':
            recorded['conclusion'] = live['conclusion'] = 'success'
    wrapper = {'schema': 'aikey-prepush-followup/1',
               'previous_record_sha256': hashlib.sha256(state['record_path'].read_bytes()).hexdigest(),
               'record': record}
    path = policy / 'docs/legal/recovery-prepush-followup.json'
    path.write_text(json.dumps(wrapper))
    state.update(followup_path=path, followup_wrapper=wrapper, followup_run=current,
                 followup_jobs=jobs)
    state['history'].insert(2, copy.deepcopy(current))
    env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '175'

    def run(argv, *, cwd, **kwargs):
        if argv[-1].endswith('/runs/175'):
            return json.dumps(state['followup_run'])
        if argv[-1].endswith('/runs/175/jobs?per_page=100'):
            return json.dumps({'total_count': 8, 'jobs': state['followup_jobs']})
        if argv == ['git', 'show', 'e' * 40 + ':.github/workflows/publish-release.yml']:
            return 'FICTIONAL second workflow\n'
        return base_run(argv, cwd=cwd, **kwargs)
    return policy, source, policy_sha, env, state, run


@pytest.mark.parametrize('fault', [
    'none', 'wrong_previous_hash', 'missing_previous', 'newer_unknown', 'third_dispatch',
    'new_rerun', 'old_rerun', 'reversed_times', 'listing_time_mismatch', 'old_graph_changed',
    'new_graph_changed', 'missing_new_job', 'new_registry_login', 'new_push',
    'new_cleanup_failure', 'new_package_failed', 'old_package_succeeded', 'extra_record_key',
])
def test_both_reviewed_preflight_runs_remain_exact_and_no_later_effects(followup_records, fault):
    policy, source, _, env, state, run = followup_records
    if fault == 'wrong_previous_hash':
        state['followup_wrapper']['previous_record_sha256'] = '0' * 64
    elif fault == 'missing_previous':
        state['record_path'].unlink()
    elif fault == 'newer_unknown':
        env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '176'
    elif fault == 'third_dispatch':
        state['history'].append({'id': 180, 'created_at': '2026-01-01T03:30:00Z'})
    elif fault in ('new_rerun', 'old_rerun'):
        state['followup_run' if fault == 'new_rerun' else 'preflight_run']['run_attempt'] = 2
    elif fault == 'reversed_times':
        state['followup_run']['created_at'] = '2026-01-01T02:30:00Z'
    elif fault == 'listing_time_mismatch':
        state['history'][2]['updated_at'] = '2026-01-01T03:21:00Z'
    elif fault in ('old_graph_changed', 'new_graph_changed'):
        state['preflight_jobs' if fault == 'old_graph_changed' else 'followup_jobs'][0]['id'] += 9
    elif fault == 'missing_new_job':
        state['followup_jobs'].pop()
    elif fault in ('new_registry_login', 'new_push', 'new_cleanup_failure'):
        name = {'new_registry_login': 'Short-lived workflow registry login',
                'new_push': 'Push only these attempt-specific images; observe immutable manifests',
                'new_cleanup_failure': 'Remove owned local fixtures and verify zero remaining resources'}[fault]
        job = next(j for j in state['followup_jobs'] if j['name'].startswith('images ('))
        step = next(s for s in job['steps'] if s['name'] == name)
        step['conclusion'] = 'failure' if fault == 'new_cleanup_failure' else 'success'
    elif fault in ('new_package_failed', 'old_package_succeeded'):
        jobs = state['followup_jobs' if fault == 'new_package_failed' else 'preflight_jobs']
        next(j for j in jobs if j['name'] == 'packages')['conclusion'] = (
            'failure' if fault == 'new_package_failed' else 'success')
    elif fault == 'extra_record_key':
        state['followup_wrapper']['allow_future'] = True
    state['followup_path'].write_text(json.dumps(state['followup_wrapper']))
    if fault == 'none':
        result = recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')
        assert result['reconciled_preflight']['run_id'] == '175'
        assert result['reconciled_preflight']['preceding_preflights'][0]['run_id'] == '150'
        assert state['ci'] == [(policy, 'a' * 40)]
    else:
        with pytest.raises((gate.PreparationError, OSError, KeyError)):
            recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')
