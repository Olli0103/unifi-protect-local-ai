"""Explicit one-camera native pairing with a retained settings snapshot.

Separate host operator, never an Admin-site credential or automatic pairing grant.
The controller has no demonstrated atomic compare-and-set API: the operator must
own a camera-maintenance window. Unknown drift or uncertain effects block replay.
"""
from __future__ import annotations

import argparse
import os
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import secrets
import time

import aiohttp

from . import camera_inventory as inventory

from .config import atomic_private
from .host_control_store import private_directory, writer
from .index_native import NativeIndexError, NativeIndexSession, _body
from .private_files import read_private
from .protocol import _json_object

FILE = 'native-pairing.json'
SCHEMA = 'aikey-native-pairing/1'
VERSIONS = {'7.3.74', '7.4.96'}
ID = re.compile(r'[0-9a-f]{24}\Z')
FIELDS = ('recordingSettings', 'smartDetectSettings', 'smartDetectZones',
          'smartDetectLines', 'smartDetectLoiterZones', 'privacyZones', 'motionZones')


class PairingError(ValueError):
    """Fixed category only; private native contents never become diagnostics."""


def encoded(value):
    try:
        raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    except (TypeError, ValueError, RecursionError):
        raise PairingError('native_pairing_invalid_json') from None
    if len(raw) > 2*1024*1024:
        raise PairingError('native_pairing_observation_too_large')
    return raw


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise PairingError('native_pairing_invalid_identity')
    return value


def observation(value):
    """Private stable fields only; omit stream aliases, credentials and media."""
    try:
        encoded(value)
        version = value['nvr']['version']
        if version not in VERSIONS:
            raise ValueError
        cameras, ports = value['cameras'], value['aiports']
        if not isinstance(cameras, list) or not 1 <= len(cameras) <= 256 or not isinstance(ports, list) or not 1 <= len(ports) <= 32:
            raise ValueError
        selected = []
        for camera in cameras:
            row = {'id': identifier(camera['id']), 'mac': camera['mac'],
                   **{key: deepcopy(camera[key]) for key in FIELDS if key in camera}}
            if (not isinstance(row['mac'], str) or not re.fullmatch('[0-9A-Fa-f]{12}', row['mac'])
                    or not isinstance(row.get('recordingSettings'), dict)
                    or not isinstance(row.get('smartDetectSettings'), dict)
                    or any(not isinstance(row.get(key), list) for key in FIELDS[2:])):
                raise ValueError
            row['channels'] = [{key: channel[key] for key in ('id', 'width', 'height', 'fps', 'enabled')}
                               for channel in camera['channels']]
            selected.append(row)
        pairings = []
        for port in ports:
            if (not isinstance(port['pairedCameras'], list) or len(port['pairedCameras']) > 5
                    or len(set(port['pairedCameras'])) != len(port['pairedCameras'])
                    or not isinstance(port['mac'], str) or not re.fullmatch('[0-9A-Fa-f]{12}', port['mac'])):
                raise ValueError
            pairings.append({'id': identifier(port['id']), 'mac': port['mac'],
                             'cameras': sorted(identifier(c) for c in port['pairedCameras'])})
        if (len({c['id'] for c in selected}) != len(selected)
                or len({c['mac'].upper() for c in selected}) != len(selected)
                or len({p['id'] for p in pairings}) != len(pairings)
                or len({p['mac'].upper() for p in pairings}) != len(pairings)):
            raise ValueError
        known = {c['id'] for c in selected}
        assigned = [c for p in pairings for c in p['cameras']]
        if not set(assigned) <= known or len(set(assigned)) != len(assigned):
            raise ValueError
        return {'version': version, 'cameras': sorted(selected, key=lambda c: c['id']),
                'ports': sorted(pairings, key=lambda p: p['id'])}
    except (KeyError, TypeError, ValueError, AttributeError):
        raise PairingError('native_pairing_observation_refused') from None


def prepare(value, camera, port, target):
    camera, port = identifier(camera), identifier(port)
    if target not in {'paired', 'unpaired'}:
        raise PairingError('native_pairing_invalid_target')
    before = observation(value)
    try:
        c = next(c for c in value['cameras'] if c['id'] == camera)
        p = next(p for p in value['aiports'] if p['id'] == port)
    except StopIteration:
        raise PairingError('native_pairing_selected_device_unavailable') from None
    if (c.get('state') != 'CONNECTED' or c.get('isRecording') is not True
            or p.get('state') != 'CONNECTED' or p.get('isAdopted') is not True
            or not isinstance(c.get('type'), str) or not re.match(r'UVC G[345](?:\s|\Z)', c['type'])):
        raise PairingError('native_pairing_selected_device_not_ready')
    owners = [p['id'] for p in before['ports'] if camera in p['cameras']]
    if owners and owners != [port]:
        raise PairingError('native_pairing_other_port_owner')
    expected = deepcopy(before)
    ids = next(p['cameras'] for p in expected['ports'] if p['id'] == port)
    if target == 'paired' and not owners:
        if len(ids) >= 5:
            raise PairingError('native_pairing_capacity_unavailable')
        ids.append(camera)
        ids.sort()
    elif target == 'unpaired' and owners:
        ids.remove(camera)
    return {'camera': camera, 'port': port, 'target': target, 'before': before, 'expected': expected}


def repair_payload(plan, current):
    """Recognize only the actually observed empty-list/zone-class reset."""
    expected = plan['expected']
    if current == expected:
        return None
    altered = deepcopy(current)
    old = next(c for c in expected['cameras'] if c['id'] == plan['camera'])
    new = next((c for c in altered['cameras'] if c['id'] == plan['camera']), None)
    if new is None or plan['target'] != 'paired':
        raise PairingError('native_pairing_unrecognized_drift')
    smart_old, smart_new = old['smartDetectSettings'], new['smartDetectSettings']
    for key in ('objectTypes', 'audioTypes'):
        if not isinstance(smart_old.get(key), list) or smart_new.get(key) != []:
            raise PairingError('native_pairing_unrecognized_drift')
    if {k: v for k, v in smart_old.items() if k not in {'objectTypes', 'audioTypes'}} != {
            k: v for k, v in smart_new.items() if k not in {'objectTypes', 'audioTypes'}}:
        raise PairingError('native_pairing_unrecognized_drift')
    zones_old, zones_new = old['smartDetectZones'], new['smartDetectZones']
    if len(zones_old) != len(zones_new):
        raise PairingError('native_pairing_unrecognized_drift')
    for a, b in zip(zones_old, zones_new):
        if (not isinstance(a.get('objectTypes'), list) or not isinstance(b.get('objectTypes'), list)
                or set(b['objectTypes']) not in (set(a['objectTypes']), set(a['objectTypes']) | {'face'})
                or {k: v for k, v in a.items() if k != 'objectTypes'} != {k: v for k, v in b.items() if k != 'objectTypes'}):
            raise PairingError('native_pairing_unrecognized_drift')
    new['smartDetectSettings'] = deepcopy(smart_old)
    new['smartDetectZones'] = deepcopy(zones_old)
    if altered != expected:
        raise PairingError('native_pairing_unrecognized_drift')
    return {'smartDetectSettings': deepcopy(smart_old), 'smartDetectZones': deepcopy(zones_old)}


def checked_plan(plan):
    if (not isinstance(plan, dict) or set(plan) != {'camera', 'port', 'target', 'authority', 'before', 'expected'}
            or not isinstance(plan['authority'], str) or not re.fullmatch('[0-9a-f]{64}', plan['authority'])):
        raise PairingError('native_pairing_journal_invalid')
    identifier(plan['camera'])
    identifier(plan['port'])
    if plan['target'] not in {'paired', 'unpaired'}:
        raise PairingError('native_pairing_journal_invalid')
    def raw(projected):
        return {'nvr': {'version': projected['version']},
                'cameras': [dict(c, type='UVC G5 Flex', state='CONNECTED', isRecording=True)
                            for c in projected['cameras']],
                'aiports': [dict(p, pairedCameras=p['cameras'], state='CONNECTED', isAdopted=True)
                           for p in projected['ports']]}
    try:
        value = raw(plan['before'])
        if observation(value) != plan['before']:
            raise ValueError
        rebuilt = prepare(value, plan['camera'], plan['port'], plan['target'])
        rebuilt['authority'] = plan['authority']
        if rebuilt != plan:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise PairingError('native_pairing_journal_invalid') from None
    return plan


def read(directory):
    path = directory / FILE
    if not path.exists() and not path.is_symlink():
        return None
    value = _json_object(read_private(path, 2*1024*1024))
    if (not isinstance(value, dict) or value.get('schema') != SCHEMA
            or value.get('phase') not in {'prepared', 'pairing', 'restoring', 'complete', 'uncertain'}
            or not isinstance(value.get('plan'), dict) or not isinstance(value.get('actions'), list)
            or len(value['actions']) > 2 or value.get('failure') not in {None, 'effect_unconfirmed'}):
        raise PairingError('native_pairing_journal_invalid')
    checked_plan(value['plan'])
    if (not isinstance(value.get('operation'), str) or not re.fullmatch('[0-9a-f]{32}', value['operation'])
            or type(value.get('created_at')) is not int or value['created_at'] < 0
            or set(value) - {'schema', 'operation', 'plan', 'phase', 'created_at', 'actions', 'failure', 'after_pairing', 'reconciliation'}):
        raise PairingError('native_pairing_journal_invalid')
    for index, action in enumerate(value['actions']):
        if (not isinstance(action, dict) or set(action) != {'action', 'state'}
                or action['state'] not in {'requested', 'observed'}
                or action['action'] != (value['plan']['target'] if index == 0 else 'restore_settings')
                or index == 1 and value['plan']['target'] != 'paired'):
            raise PairingError('native_pairing_journal_invalid')
    if value['phase'] == 'complete' and any(a['state'] != 'observed' for a in value['actions']):
        if not value.get('reconciliation'):
            raise PairingError('native_pairing_journal_invalid')
    return value


def archive(directory, value):
    root = directory / 'history'
    root.mkdir(mode=0o700, exist_ok=True)
    private_directory(root, PairingError)
    destination = root / (value['operation']+'.json')
    raw = encoded(value)
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if read_private(destination, 2*1024*1024) != raw:
            raise PairingError('native_pairing_history_conflict') from None
    else:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    handle = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)



async def run(client, directory, *, camera, port, target, apply=False, reconcile=False):
    """One explicit operation; no retries, implicit unpair, rollback or model call."""
    directory = private_directory(Path(directory), PairingError)
    with writer(directory, mutate=apply or reconcile, error=PairingError) as (_, bound):
        authority = client.authority
        if not isinstance(authority, str) or not re.fullmatch('[0-9a-f]{64}', authority):
            raise PairingError('native_pairing_authority_unavailable')
        retained = read(directory)
        if retained is not None and retained['plan']['authority'] != authority:
            raise PairingError('native_pairing_controller_changed')
        if retained is not None and reconcile:
            plan = retained['plan']
            if (plan['camera'], plan['port'], plan['target']) != (camera, port, target):
                raise PairingError('native_pairing_journal_scope_changed')
            observed = observation(await client.bootstrap())
            no_effect = not retained['actions'] and observed == plan['before']
            if not no_effect and observed != plan['expected']:
                raise PairingError('native_pairing_not_reconciled_no_effects')
            retained['phase'] = 'complete'
            retained['reconciliation'] = {'writes': 0, 'original_failure_retained': True,
                                          'target_reached': not no_effect}
            bound()
            atomic_private(directory / FILE, encoded(retained))
            return {'mode': 'reconciled', 'writes': 0, 'settings_preserved': True, 'target_reached': not no_effect}
        if retained is not None and retained['phase'] != 'complete':
            raise PairingError('native_pairing_pending_requires_reconcile')
        if reconcile:
            raise PairingError('native_pairing_no_attempt_to_reconcile')
        plan = prepare(await client.bootstrap(), camera, port, target)
        plan['authority'] = authority
        if plan['before'] == plan['expected']:
            return {'mode': 'unchanged', 'writes': 0, 'settings_preserved': True}
        if not apply:
            return {'mode': 'preview', 'writes': 0, 'revision': digest(plan)}
        if retained is not None:
            bound()
            archive(directory, retained)
        receipt = {'schema': SCHEMA, 'operation': secrets.token_hex(16), 'plan': plan,
                   'phase': 'prepared', 'created_at': int(time.time()), 'actions': [], 'failure': None}
        def save():
            bound()
            atomic_private(directory / FILE, encoded(receipt))
        save()
        try:
            fresh = await client.bootstrap()
            fresh_plan = prepare(fresh, camera, port, target)
            fresh_plan['authority'] = authority
            if fresh_plan != plan:
                raise PairingError('native_pairing_pre_effect_drift')
            receipt['phase'] = 'pairing'
            receipt['actions'].append({'action': target, 'state': 'requested'})
            save()
            await client.set_pairing(camera, port, target)
            paired = await client.bootstrap()
            prepare(paired, camera, port, target)
            after = observation(paired)
            payload = repair_payload(plan, after)
            receipt['actions'][-1]['state'] = 'observed'
            receipt['after_pairing'] = after
            if payload is not None:
                # No native CAS exists: require the just-observed complete
                # projection again, rather than overwriting an intervening edit.
                if observation(await client.bootstrap()) != after:
                    raise PairingError('native_pairing_pre_restore_drift')
                receipt['phase'] = 'restoring'
                receipt['actions'].append({'action': 'restore_settings', 'state': 'requested'})
                save()
                await client.restore_settings(camera, payload)
            final = await client.bootstrap()
            chosen = next(c for c in final['cameras'] if c['id'] == camera)
            if (observation(final) != plan['expected'] or chosen.get('isRecording') is not True
                    or chosen.get('state') != 'CONNECTED'):
                raise PairingError('native_pairing_final_readback_failed')
            receipt['actions'][-1]['state'] = 'observed'
            receipt['phase'] = 'complete'
            save()
            return {'mode': 'applied', 'writes': len(receipt['actions']), 'settings_preserved': True,
                    'native_default_reset_repaired': payload is not None}
        except BaseException as error:
            receipt['phase'] = 'uncertain'
            receipt['failure'] = 'effect_unconfirmed'
            save()
            if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                raise
            raise PairingError('native_pairing_uncertain_inspect_do_not_retry') from None


class NativePairingSession:
    """Separate opt-in write consumer; never added to metadata/Admin readers."""
    def __init__(self, host, *, camera, port, **credentials):
        self.camera, self.port = identifier(camera), identifier(port)
        self.native = NativeIndexSession(host, **credentials)

    async def __aenter__(self):
        await self.native.__aenter__()
        try:
            pin = self.native._session.connector._pin
            if self.native.protect_version not in VERSIONS or not isinstance(pin, bytes) or len(pin) != 32:
                raise PairingError('native_pairing_unsupported_version_or_pin')
            self.authority = digest({'origin': self.native._origin, 'certificate_sha256': pin.hex()})
            return self
        except BaseException:
            await self.native.__aexit__()
            raise

    async def __aexit__(self, *args):
        return await self.native.__aexit__(*args)

    async def bootstrap(self):
        return await self.native._json('/proxy/protect/api/bootstrap', 2*1024*1024)

    async def _write(self, method, path, payload):
        session = self.native._session
        if session is None or not session.headers.get('X-CSRF-Token'):
            raise PairingError('native_pairing_authenticated_write_unavailable')
        # Native 207 multi-status isn't success evidence: the engine requires
        # exact fresh full-state readback before acknowledging the effect.
        try:
            async with session.request(method, self.native._origin+path, json=payload,
                                       allow_redirects=False) as response:
                raw = await _body(response, 2*1024*1024)
                if response.status not in {200, 207} or response.content_type != 'application/json':
                    raise PairingError('native_pairing_write_unconfirmed')
                reply = inventory._json(raw)
                encoded(reply)
                if not isinstance(reply, (dict, list)):
                    raise PairingError('native_pairing_write_unconfirmed')
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError, inventory.InventoryError):
            raise PairingError('native_pairing_write_unconfirmed') from None


    async def set_pairing(self, camera, port, target):
        if (camera, port) != (self.camera, self.port) or target not in {'paired', 'unpaired'}:
            raise PairingError('native_pairing_write_scope_refused')
        action = 'pair' if target == 'paired' else 'unpair'
        await self._write('POST', f'/proxy/protect/api/aiports/{self.port}/{action}', {'cameraIds': [self.camera]})

    async def restore_settings(self, camera, payload):
        if camera != self.camera or set(payload) != {'smartDetectSettings', 'smartDetectZones'}:
            raise PairingError('native_pairing_write_scope_refused')
        await self._write('PATCH', '/proxy/protect/api/cameras/'+self.camera, payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', required=True)
    parser.add_argument('--camera', required=True)
    parser.add_argument('--port', required=True)
    parser.add_argument('--target', choices=('paired', 'unpaired'), required=True)
    parser.add_argument('--state-dir', type=Path, required=True, help='One persistent private controller authority directory; never replace it to bypass pending intent')
    for field in ('username', 'password', 'trust', 'cert'):
        parser.add_argument('--'+field+'-file', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--reconcile', action='store_true', help='Observe only, never retry writes')
    parser.add_argument('--exclusive-camera-maintenance', action='store_true',
                        help='Operator owns this camera window; no concurrent native setting edits')
    args = parser.parse_args(argv)
    if args.apply and not args.exclusive_camera_maintenance:
        parser.error('--apply requires an exclusive camera-maintenance window')
    async def execute():
        async with NativePairingSession(args.controller, camera=args.camera, port=args.port,
                username_file=args.username_file, password_file=args.password_file,
                trust_file=args.trust_file, cert_file=args.cert_file) as client:
            return await run(client, args.state_dir, camera=args.camera, port=args.port,
                             target=args.target, apply=args.apply, reconcile=args.reconcile)
    try:
        print(json.dumps(asyncio.run(execute()), sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({'error': 'native_pairing_interrupted_inspect_attempt', 'automatic_retry': False}))
        return 130
    except (OSError, ValueError, RuntimeError, NativeIndexError):
        print(json.dumps({'error': 'native_pairing_refused_or_uncertain', 'automatic_retry': False,
                          'inspect_private_attempt': True}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
