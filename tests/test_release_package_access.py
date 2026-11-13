"""Fictional package credentials; no GitHub access, signatures or real writes."""
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from test_release_publication import publication, plan
from test_release_recovery import followup_records  # noqa: F401
from test_release_recovery import prepush_records, records, recovery, gate  # noqa: F401


ARGV = ['gh', 'api', '--paginate', '--slurp',
        f'users/{publication.gate.OWNER}/packages?package_type=container&per_page=100']
TOKEN = 'FICTIONAL_PACKAGE_READ_CANARY'


@pytest.mark.parametrize('fault', ['none', '401', '403', '404', '429', '502', 'unknown',
                                   'timeout', 'os_error', 'oversize', 'invalid_utf8'])
def test_package_read_uses_separate_token_and_fixed_diagnostics(tmp_path, monkeypatch, fault):
    monkeypatch.setenv('RELEASE_PACKAGES_READ_TOKEN', TOKEN)
    monkeypatch.setenv('GH_TOKEN', 'FICTIONAL_WORKFLOW_TOKEN')
    monkeypatch.setenv('GITHUB_TOKEN', 'FICTIONAL_OTHER_TOKEN')
    monkeypatch.setenv('GH_DEBUG', 'api')
    monkeypatch.setenv('GH_HOST', 'FICTIONAL-other-host')
    calls = []

    def run(argv, **options):
        calls.append(argv)
        assert argv in (ARGV, ['gh', 'api', 'user']) and options['cwd'] == tmp_path
        assert options['timeout'] == 20 and options['stdin'] == subprocess.DEVNULL
        env = options['env']
        assert env['GH_TOKEN'] == TOKEN and env['GH_HOST'] == 'github.com'
        assert not {'GITHUB_TOKEN', 'GH_DEBUG', 'RELEASE_PACKAGES_READ_TOKEN'} & env.keys()
        if fault == 'timeout':
            raise subprocess.TimeoutExpired(argv, 20)
        if fault == 'os_error':
            raise OSError(TOKEN)
        if fault in {'401', '403', '404', '429', '502', 'unknown'}:
            options['stderr'].write((TOKEN + ' (HTTP ' + fault + ')').encode())
            return SimpleNamespace(returncode=1)
        if argv == ['gh', 'api', 'user'] and fault == 'none':
            options['stdout'].write(json.dumps({'login': publication.gate.OWNER, 'id': publication.gate.OWNER_ID, 'type': 'User'}).encode())
            return SimpleNamespace(returncode=0)
        options['stdout'].write(b'x' * (128 * 1024 + 1) if fault == 'oversize'
                                else b'\xff' if fault == 'invalid_utf8' else b'[[]]')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(publication.subprocess, 'run', run)
    if fault == 'none':
        assert publication.package_metadata(ARGV, cwd=tmp_path) == '[[]]'
    else:
        with pytest.raises(ValueError) as error:
            publication.package_metadata(ARGV, cwd=tmp_path)
        assert TOKEN not in str(error.value)
        if fault.isnumeric():
            assert str(error.value) == 'release_package_metadata_http_' + fault
    assert calls == ([['gh', 'api', 'user'], ARGV] if fault == 'none' else [['gh', 'api', 'user']])


@pytest.mark.parametrize('token', ['', 'bad token', 'bad\ntoken', 'x' * 4097])
def test_missing_or_invalid_package_token_fails_before_subprocess(tmp_path, monkeypatch, token):
    monkeypatch.setenv('RELEASE_PACKAGES_READ_TOKEN', token)
    monkeypatch.setattr(publication.subprocess, 'run', lambda *a, **k: pytest.fail('unexpected effect'))
    with pytest.raises(publication.PublicationError, match='release_package_read_token_required'):
        publication.package_metadata(ARGV, cwd=tmp_path)


@pytest.mark.parametrize('argv', [ARGV[:-1] + ['https://example.invalid/'],
                                ['gh', 'api', '-X', 'POST', ARGV[-1]],
                                ARGV + ['--hostname', 'example.invalid']])
def test_package_token_never_reaches_other_commands_or_hosts(tmp_path, monkeypatch, argv):
    monkeypatch.setenv('RELEASE_PACKAGES_READ_TOKEN', TOKEN)
    monkeypatch.setattr(publication.subprocess, 'run', lambda *a, **k: pytest.fail('unexpected effect'))
    with pytest.raises(publication.PublicationError, match='command_refused'):
        publication.package_metadata(argv, cwd=tmp_path)


def test_default_privacy_observation_routes_only_catalogue_to_separate_token(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(publication, 'package_metadata',
                        lambda argv, **kwargs: calls.append(argv) or '[[]]')
    publication.private_images(tmp_path, plan(), allow_missing=True)
    assert calls == [ARGV]
    publication.private_images(tmp_path, dict(plan(), images={}))
    assert calls == [ARGV]


def test_workflow_probes_before_staging_and_keeps_native_build_and_login_token_separate():
    jobs = yaml.safe_load((Path(__file__).resolve().parents[1] /
                           '.github/workflows/publish-release.yml').read_text())['jobs']
    checks = [s for s in jobs['qualify']['steps'] if 'package-access' in s.get('run', '')]
    assert len(checks) == 1 and checks[0]['if'] == "inputs.publish && inputs.profile == 'image'"
    assert checks[0]['env'] == {'RELEASE_PACKAGES_READ_TOKEN': '${{ secrets.RELEASE_PACKAGES_READ_TOKEN }}'}
    assert jobs['reserve']['needs'] == 'qualify' and jobs['reserve']['environment'] == 'release-stage'
    assert jobs['publish']['environment'] == 'release'
    for job in ('images', 'assemble'):
        assert 'RELEASE_PACKAGES_READ_TOKEN' not in jobs[job]['env']
        for step in jobs[job]['steps']:
            if step.get('uses', '').startswith('docker/login-action@'):
                assert step['with']['password'] == '${{ github.token }}'
            if any(word in step.get('run', '') for word in ('context', 'scanner', ' cleanup', ' build')):
                assert 'RELEASE_PACKAGES_READ_TOKEN' not in step.get('env', {})
    assert jobs['publish']['env']['GH_TOKEN'] == '${{ github.token }}'


@pytest.fixture
def package_records(followup_records):  # noqa: F811
    policy, source, policy_sha, env, state, base_run = followup_records
    previous = state['followup_run']
    latest = copy.deepcopy(previous)
    latest.update(id=180, head_sha='f' * 40, created_at='2026-01-01T03:30:00Z',
                  updated_at='2026-01-01T03:40:00Z')
    record = copy.deepcopy(state['followup_wrapper']['record'])
    record.update(run_id='180', policy_revision='f' * 40,
                  workflow_sha256=hashlib.sha256(b'FICTIONAL package workflow\n').hexdigest())
    jobs = copy.deepcopy(state['followup_jobs'])
    states = {'Bind pre-push intent to tested image configs and inventories': 'success',
              'Short-lived workflow registry login': 'success',
              'Push only these attempt-specific images; observe immutable manifests': 'failure'}
    for recorded, live in zip(record['jobs'], jobs, strict=True):
        recorded['id'] += 1000
        live['id'] += 1000
        for rs, ls in zip(recorded['steps'], live['steps'], strict=True):
            if live['name'].startswith('images (') and ls['name'] in states:
                rs['conclusion'] = ls['conclusion'] = states[ls['name']]
    wrapper = {'schema': 'aikey-package-read-reconciliation/1',
               'previous_record_sha256': hashlib.sha256(state['followup_path'].read_bytes()).hexdigest(),
               'record': record}
    path = policy / 'docs/legal/recovery-package-read.json'
    path.write_text(json.dumps(wrapper))
    state.update(package_path=path, package_wrapper=wrapper, package_jobs=jobs, package_run=latest)
    state['history'].insert(3, copy.deepcopy(latest))
    env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '180'

    def run(argv, *, cwd, **kwargs):
        if argv[-1].endswith('/runs/180'):
            return json.dumps(state['package_run'])
        if argv[-1].endswith('/runs/180/jobs?per_page=100'):
            return json.dumps({'total_count': len(state['package_jobs']), 'jobs': state['package_jobs']})
        if argv == ['git', 'show', 'f' * 40 + ':.github/workflows/publish-release.yml']:
            return 'FICTIONAL package workflow\n'
        return base_run(argv, cwd=cwd, **kwargs)
    return policy, source, policy_sha, env, state, run


@pytest.mark.parametrize('fault', ['none', 'hash', 'extra', 'wrong_run', 'rerun', 'active',
                                   'unknown_later', 'inverted_time', 'push_success',
                                   'cleanup_failure', 'changed_step', 'old_changed', 'missing_job'])
def test_third_reconciliation_requires_exact_three_graphs_and_no_unreviewed_retry(package_records, fault):
    policy, source, _, env, state, run = package_records
    if fault == 'hash':
        state['package_wrapper']['previous_record_sha256'] = '0' * 64
    elif fault == 'extra':
        state['package_wrapper']['allow_retry'] = True
    elif fault == 'wrong_run':
        env['RELEASE_RECOVERY_PREFLIGHT_RUN'] = '181'
    elif fault == 'rerun':
        state['package_run']['run_attempt'] = 2
    elif fault == 'active':
        state['package_run']['status'] = 'in_progress'
    elif fault == 'unknown_later':
        state['history'].append({'id': 190, 'created_at': '2026-01-01T03:50:00Z'})
    elif fault == 'inverted_time':
        state['history'][3]['created_at'] = '2026-01-01T03:00:00Z'
    elif fault == 'old_changed':
        state['preflight_jobs'][0]['id'] += 3
    elif fault == 'missing_job':
        state['package_jobs'].pop()
    elif fault in {'push_success', 'cleanup_failure', 'changed_step'}:
        job = next(j for j in state['package_jobs'] if j['name'].startswith('images ('))
        name = ('Push only these attempt-specific images; observe immutable manifests'
                if fault == 'push_success' else 'Remove owned local fixtures and verify zero remaining resources')
        step = next(s for s in job['steps'] if s['name'] == name)
        if fault == 'changed_step':
            step['name'] += ' changed'
        else:
            step['conclusion'] = 'success' if fault == 'push_success' else 'failure'
    state['package_path'].write_text(json.dumps(state['package_wrapper']))
    if fault == 'none':
        value = recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')
        assert value['reconciled_preflight']['run_id'] == '180'
        assert [r['run_id'] for r in value['reconciled_preflight']['preceding_preflights']] == ['150', '175']
    else:
        with pytest.raises((gate.PreparationError, OSError, KeyError)):
            recovery.context(policy.parent / 'source', source, gate, env, run, profile='image')


@pytest.mark.parametrize('fault', ['wrong_login', 'wrong_id', 'boolean_id', 'bot'])
def test_package_reader_requires_actual_owner_before_catalogue(tmp_path, monkeypatch, fault):
    monkeypatch.setenv('RELEASE_PACKAGES_READ_TOKEN', TOKEN)
    person = {'login': publication.gate.OWNER, 'id': publication.gate.OWNER_ID, 'type': 'User'}
    key, value = {'wrong_login': ('login', 'FICTIONAL-other'), 'wrong_id': ('id', 1),
                  'boolean_id': ('id', True), 'bot': ('type', 'Bot')}[fault]
    person[key] = value
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        assert argv == ['gh', 'api', 'user']
        kwargs['stdout'].write(json.dumps(person).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(publication.subprocess, 'run', run)
    with pytest.raises(publication.PublicationError, match='owner_required'):
        publication.package_metadata(ARGV, cwd=tmp_path)
    assert len(calls) == 1
