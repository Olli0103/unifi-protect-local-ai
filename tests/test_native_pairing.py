"""Bundled native pairing transactions, uncertainty and real pinned TLS; fictional only."""
import asyncio
from copy import deepcopy
import json

from aiohttp import web
import pytest

from aikey import native_pairing as guard
from test_native_camera_status import controller

CAMERA, OTHER, PORT = 'a'*24, 'b'*24, 'c'*24


def bootstrap(paired=False):
    settings = {'recordingSettings': {'mode': 'always', 'recordVideo': True},
                'smartDetectSettings': {'objectTypes': ['person', 'animal'], 'audioTypes': ['alrmSpeak'], 'other': True},
                'smartDetectZones': [{'id': 1, 'objectTypes': ['person'], 'sensitivity': 50, 'points': [[0, 0], [1, 0], [1, 1]]}],
                'smartDetectLines': [], 'smartDetectLoiterZones': [], 'motionZones': [], 'privacyZones': [],
                'channels': [{'id': 0, 'width': 1920, 'height': 1080, 'fps': 20, 'enabled': True}],
                'isRecording': True, 'state': 'CONNECTED', 'type': 'UVC G5 Flex'}
    return {'nvr': {'version': '7.4.96'}, 'cameras': [dict(deepcopy(settings), id=CAMERA, mac='020000000001', private='CANARY'),
            dict(deepcopy(settings), id=OTHER, mac='020000000002')],
            'aiports': [{'id': PORT, 'mac': '020000000003', 'pairedCameras': [CAMERA] if paired else [],
                         'state': 'CONNECTED', 'isAdopted': True}]}


class Client:
    authority = '1'*64
    def __init__(self, paired=False, failure=None):
        self.value = bootstrap(paired)
        self.failure = failure
        self.calls = []
        self.reads = 0

    async def bootstrap(self):
        self.reads += 1
        if self.failure == 'before' and self.reads == 2:
            self.value['cameras'][1]['recordingSettings']['mode'] = 'never'
        if self.failure == 'before_restore' and self.reads == 4:
            self.value['cameras'][1]['smartDetectZones'][0]['sensitivity'] = 90
        return deepcopy(self.value)

    async def set_pairing(self, camera, port, target):
        self.calls.append(target)
        assert (camera, port) == (CAMERA, PORT)
        if target == 'paired':
            self.value['aiports'][0]['pairedCameras'] = [camera]
            c = self.value['cameras'][0]
            c['smartDetectSettings']['objectTypes'] = []
            c['smartDetectSettings']['audioTypes'] = []
            c['smartDetectZones'][0]['objectTypes'].append('face')
        else:
            self.value['aiports'][0]['pairedCameras'] = []
        if self.failure == 'unknown':
            self.value['cameras'][0]['smartDetectZones'][0]['sensitivity'] = 99
        if self.failure == 'lost_pair':
            raise RuntimeError('CANARY-private-native-error')
        if self.failure == 'cancel':
            raise asyncio.CancelledError

    async def restore_settings(self, camera, payload):
        assert camera == CAMERA
        self.calls.append('restore')
        if self.failure == 'lost_restore':
            self.value['cameras'][0].update(deepcopy(payload))
            raise RuntimeError('CANARY-private-ack-loss')
        self.value['cameras'][0].update(deepcopy(payload))


@pytest.fixture
def directory(tmp_path):
    root = tmp_path/'authority'
    root.mkdir(mode=0o700)
    return root


async def operate(client, root, **kwargs):
    return await guard.run(client, root, camera=CAMERA, port=PORT, target='paired', **kwargs)


async def test_complete_pair_unpair_lifecycle_preview_private_archive_and_noop(directory):
    client = Client()
    original = guard.observation(client.value)
    preview = await operate(client, directory)
    assert preview['mode'] == 'preview' and client.calls == [] and list(directory.iterdir()) == []
    result = await operate(client, directory, apply=True)
    assert result == {'mode': 'applied', 'writes': 2, 'settings_preserved': True, 'native_default_reset_repaired': True}
    assert client.calls == ['paired', 'restore']
    first = guard.read(directory)
    assert first['phase'] == 'complete' and all(a['state'] == 'observed' for a in first['actions'])
    assert 'CANARY' not in json.dumps(first) and 'CANARY' not in json.dumps(result)
    assert (directory/guard.FILE).stat().st_mode & 0o777 == 0o600
    assert (await operate(client, directory, apply=True))['mode'] == 'unchanged'
    result = await guard.run(client, directory, camera=CAMERA, port=PORT, target='unpaired', apply=True)
    assert result['writes'] == 1 and client.calls == ['paired', 'restore', 'unpaired']
    assert guard.observation(client.value) == original
    saved = next((directory/'history').iterdir())
    assert json.loads(saved.read_text()) == first and saved.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('failure,expected_calls', [
    ('before', []), ('unknown', ['paired']), ('before_restore', ['paired']),
    ('lost_pair', ['paired']), ('lost_restore', ['paired', 'restore'])])
async def test_drift_and_lost_acknowledgements_are_durable_no_retry(directory, failure, expected_calls):
    client = Client(failure=failure)
    with pytest.raises(guard.PairingError, match='uncertain_inspect'):
        await operate(client, directory, apply=True)
    receipt = (directory/guard.FILE).read_bytes()
    assert client.calls == expected_calls
    assert guard.read(directory)['phase'] == 'uncertain'
    client.failure = None
    with pytest.raises(guard.PairingError, match='pending_requires_reconcile'):
        await operate(client, directory, apply=True)
    assert client.calls == expected_calls and (directory/guard.FILE).read_bytes() == receipt
    if failure == 'lost_restore':
        result = await operate(client, directory, reconcile=True)
        assert result['mode'] == 'reconciled' and result['writes'] == 0
        assert guard.read(directory)['failure'] == 'effect_unconfirmed'
        assert guard.read(directory)['reconciliation']['original_failure_retained'] is True
    else:
        with pytest.raises(guard.PairingError, match='not_reconciled'):
            await operate(client, directory, reconcile=True)
    assert client.calls == expected_calls


async def test_cancellation_is_not_relabelled_success_or_retried(directory):
    client = Client(failure='cancel')
    with pytest.raises(asyncio.CancelledError):
        await operate(client, directory, apply=True)
    assert guard.read(directory)['phase'] == 'uncertain' and client.calls == ['paired']


async def test_journal_is_controller_bound_and_corrupt_private_files_refused(directory):
    client = Client()
    await operate(client, directory, apply=True)
    client.authority = '2'*64
    with pytest.raises(guard.PairingError, match='controller_changed'):
        await operate(client, directory, reconcile=True)
    assert client.calls == ['paired', 'restore']
    client.authority = '1'*64
    path = directory/guard.FILE
    raw = path.read_bytes()
    path.write_text('{"schema":1,"schema":2}')
    with pytest.raises(ValueError):
        await operate(client, directory, apply=True)
    path.write_bytes(raw)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        await operate(client, directory, apply=True)
    path.chmod(0o600)
    assert len(client.calls) == 2


@pytest.mark.parametrize('fault', ['version', 'other_owner', 'offline', 'recording', 'duplicate', 'source'])
async def test_unready_or_ambiguous_admission_has_no_native_write(directory, fault):
    client = Client()
    if fault == 'version':
        client.value['nvr']['version'] = '7.4.97'
    elif fault == 'other_owner':
        p = deepcopy(client.value['aiports'][0])
        p.update(id='d'*24, mac='020000000004', pairedCameras=[CAMERA])
        client.value['aiports'].append(p)
    elif fault == 'offline':
        client.value['cameras'][0]['state'] = 'DISCONNECTED'
    elif fault == 'recording':
        client.value['cameras'][0]['isRecording'] = False
    elif fault == 'duplicate':
        client.value['cameras'].append(deepcopy(client.value['cameras'][0]))
    elif fault == 'source':
        client.value['cameras'][0]['type'] = 'ONVIF synthetic'
    with pytest.raises(guard.PairingError):
        await operate(client, directory, apply=True)
    assert client.calls == [] and not (directory/guard.FILE).exists()


async def test_actual_pinned_tls_pair_and_repair_with_exact_paths_and_fresh_readback(tmp_path, monkeypatch, directory):
    client = Client()
    changes = []
    async def pair(request):
        assert request.cookies['TOKEN'] == 'FICTIONAL-SESSION'
        assert request.headers['X-CSRF-Token'] == 'FICTIONAL-CSRF'
        assert await request.json() == {'cameraIds': [CAMERA]}
        changes.append((request.method, request.path))
        await client.set_pairing(CAMERA, PORT, 'paired')
        return web.json_response({'status': 'synthetic-multistatus'}, status=207)
    async def patch(request):
        assert request.cookies['TOKEN'] == 'FICTIONAL-SESSION'
        assert request.headers['X-CSRF-Token'] == 'FICTIONAL-CSRF'
        payload = await request.json()
        assert set(payload) == {'smartDetectSettings', 'smartDetectZones'}
        changes.append((request.method, request.path))
        await client.restore_settings(CAMERA, payload)
        return web.json_response({'acknowledged': True})
    async with controller(tmp_path, monkeypatch, payload=client.value, additional_routes=[
            web.post('/proxy/protect/api/aiports/'+PORT+'/pair', pair),
            web.patch('/proxy/protect/api/cameras/'+CAMERA, patch)]) as (reader, seen, _):
        native = guard.NativePairingSession(reader.host, camera=CAMERA, port=PORT,
            username_file=reader.username_file, password_file=reader.password_file,
            trust_file=reader.trust_file, cert_file=reader.cert_file)
        async with native:
            result = await operate(native, directory, apply=True)
            with pytest.raises(guard.PairingError, match='scope_refused'):
                await native.set_pairing(OTHER, PORT, 'paired')
        assert result['native_default_reset_repaired'] and len(changes) == 2
        assert native.native.logout_acknowledged and native.native._session is None
        assert seen[-1] == ('POST', '/api/auth/logout')


@pytest.mark.parametrize('response', ['redirect', 'error', 'false_ack', 'invalid'])
async def test_write_transport_refusal_or_false_ack_is_not_retry_permission(tmp_path, monkeypatch, directory, response):
    client = Client()
    writes = []
    async def pair(request):
        writes.append(request.path)
        if response == 'redirect':
            return web.Response(status=307, headers={'Location': '/leak'})
        if response == 'error':
            return web.Response(status=500, text='CANARY-private')
        if response == 'invalid':
            return web.Response(text='{"ack":1,"ack":2}', content_type='application/json')
        return web.json_response({'ack': True})  # HTTP success, but no actual pairing.
    async with controller(tmp_path, monkeypatch, payload=client.value, additional_routes=[
            web.post('/proxy/protect/api/aiports/'+PORT+'/pair', pair)]) as (reader, seen, _):
        native = guard.NativePairingSession(reader.host, camera=CAMERA, port=PORT,
            username_file=reader.username_file, password_file=reader.password_file,
            trust_file=reader.trust_file, cert_file=reader.cert_file)
        async with native:
            with pytest.raises(guard.PairingError, match='uncertain_inspect'):
                await operate(native, directory, apply=True)
        assert len(writes) == 1 and native.native.logout_acknowledged
        assert guard.read(directory)['phase'] == 'uncertain'
