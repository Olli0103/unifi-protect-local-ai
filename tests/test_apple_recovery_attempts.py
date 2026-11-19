"""Recovery receipts must settle the issuing request, not a different retry.

Only invented Host adapters, private temporary journals and synthetic receipts.
"""
import os

import pytest

from aikey import apple_supervisor as supervisor
from aikey import apple_upgrade as upgrade
from aikey import apple_upgrade_state as journal
from aikey.apple_upgrade_recovery import recover
from aikey.host_runtime_command import publish_effect
from test_apple_upgrade import Host, _entry, OLD, NEW, NEW_IMAGE


def _interrupted_candidate(directory):
    host = Host([_entry()])
    supervisor.pin(directory, "aiport-mac", OLD, run=host)
    planned = upgrade.plan(directory, "aiport-mac", NEW, NEW_IMAGE, run=host)

    def cut():
        raise KeyboardInterrupt("synthetic readiness cut")

    with pytest.raises(KeyboardInterrupt):
        upgrade.swap(directory, planned, idle=lambda: True, ready=cut, run=host)
    return host


def _publish(directory, context, *, spawned=True, exit_code=0, error=None):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        publish_effect(descriptor, context, {
            "spawned": spawned, "command_terminal": True,
            "exit_code": exit_code, "error": error,
        })
    finally:
        os.close(descriptor)


def _twice_interrupted(directory, action, evidence):
    host = _interrupted_candidate(directory)
    targeted = []
    verb = {"stop_new": "stop", "delete_new": "delete", "restart_old": "start"}[action]

    def effect(argv, context):
        if context["action"].startswith("recover_" + action + "_"):
            targeted.append(context["action"])
            assert argv[1] == verb
            # A successful CLI exit does not establish the requested state.
            # Leave the state unobserved and cut before the parent's ACK.
            if len(targeted) == 1:
                _publish(directory, context)
            elif evidence == "success":
                _publish(directory, context)
            elif evidence == "no_spawn":
                _publish(directory, context, spawned=False, exit_code=None, error="owner_lost")
            elif evidence == "failed":
                _publish(directory, context, exit_code=1)
            elif evidence == "wrong_digest":
                _publish(directory, dict(context, argv_sha256="e" * 64))
            raise KeyboardInterrupt("synthetic cut before recovery ACK")
        result = host(argv)
        _publish(directory, context, exit_code=result[0])
        return result

    host.with_effect = effect
    for _ in range(2):
        with pytest.raises(KeyboardInterrupt):
            recover(directory, "aiport-mac", ready=lambda: True, run=host)
    assert targeted == [f"recover_{action}_1", f"recover_{action}_2"]
    del host.with_effect
    host.calls.clear()
    return host


@pytest.mark.parametrize("action", ["stop_new", "delete_new", "restart_old"])
@pytest.mark.parametrize("evidence", ["missing", "failed", "wrong_digest"])
def test_older_terminal_receipt_never_settles_an_unknown_later_request(tmp_path, action, evidence):
    host = _twice_interrupted(tmp_path, action, evidence)
    before = (tmp_path / journal.FILE).read_bytes()
    outcome = recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    assert outcome in {"recovery_command_unsettled", "recovery_outcome_uncertain"}
    assert host.calls == []
    assert (tmp_path / journal.FILE).read_bytes() == before
    assert journal.pending(tmp_path) is not None


@pytest.mark.parametrize("action", ["stop_new", "delete_new", "restart_old"])
@pytest.mark.parametrize("evidence", ["success", "no_spawn"])
def test_exact_current_terminal_or_no_spawn_receipt_allows_reconciliation(tmp_path, action, evidence):
    host = _twice_interrupted(tmp_path, action, evidence)
    pending = journal.pending(tmp_path)
    assert pending["recovery_command_attempts"][action] == 2
    assert recover(tmp_path, "aiport-mac", ready=lambda: True, run=host) == "recovered_old"
    assert journal.pending(tmp_path) is None
    assert NEW not in host.entries and host.entries[OLD]["status"]["state"] == "running"
    assert journal.read(tmp_path)["failure"] == pending["failure"]


@pytest.mark.parametrize("legacy", [False, True])
def test_bound_request_survives_a_later_attempt_cut_before_observation(tmp_path, monkeypatch, legacy):
    host = _interrupted_candidate(tmp_path)

    def effect(argv, context):
        result = host(argv)
        _publish(tmp_path, context, exit_code=result[0])
        if context["action"] == "recover_restart_old_1":
            raise KeyboardInterrupt("synthetic cut after restart result before ACK")
        return result

    host.with_effect = effect
    with pytest.raises(KeyboardInterrupt):
        recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    del host.with_effect
    if legacy:
        import json
        value = journal.pending(tmp_path)
        value.pop("recovery_command_attempts")
        (tmp_path / journal.FILE).write_text(json.dumps(value))
    record = journal.recovery_step

    def cut(directory, value, action, state, bound):
        if (action, state) == ("restart_old", "observed"):
            raise KeyboardInterrupt("synthetic cut after attempt increment")
        return record(directory, value, action, state, bound)

    with monkeypatch.context() as patch:
        patch.setattr(journal, "recovery_step", cut)
        with pytest.raises(KeyboardInterrupt):
            recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    value = journal.pending(tmp_path)
    assert value["recovery_attempts"] == 2
    assert value["recovery_command_attempts"]["restart_old"] == 1
    host.calls.clear()
    assert recover(tmp_path, "aiport-mac", ready=lambda: True, run=host) == "recovered_old"
    assert all(call[0] == "list" for call in host.calls)


@pytest.mark.parametrize("attempt", [0, -1, 3, True, "2", None])
def test_invalid_request_attempt_is_not_readable(tmp_path, attempt):
    host = _twice_interrupted(tmp_path, "restart_old", "missing")
    value = journal.pending(tmp_path)
    value["recovery_command_attempts"] = {"restart_old": attempt}
    import json
    (tmp_path / journal.FILE).write_text(json.dumps(value))
    with pytest.raises(journal.UpgradeStateError):
        recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    assert host.calls == []


@pytest.mark.parametrize("repeated", [False, True])
def test_legacy_unbound_request_is_only_inferred_for_one_recovery_attempt(tmp_path, repeated):
    import json
    if repeated:
        host = _twice_interrupted(tmp_path, "restart_old", "missing")
    else:
        host = _interrupted_candidate(tmp_path)

        def effect(argv, context):
            assert context["action"] == "recover_stop_new_1"
            _publish(tmp_path, context)
            raise KeyboardInterrupt("synthetic first request cut")

        host.with_effect = effect
        with pytest.raises(KeyboardInterrupt):
            recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
        del host.with_effect
        host.calls.clear()
    value = journal.pending(tmp_path)
    value.pop("recovery_command_attempts", None)
    (tmp_path / journal.FILE).write_text(json.dumps(value))
    before = (tmp_path / journal.FILE).read_bytes()
    result = recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    if repeated:
        assert result == "recovery_command_unsettled"
        assert host.calls == [] and (tmp_path / journal.FILE).read_bytes() == before
    else:
        assert result == "recovered_old"


@pytest.mark.parametrize("mapping", [None, [], {"hold": 1}, {"unrecognized": 1}])
def test_malformed_command_attempt_map_never_reaches_the_host(tmp_path, mapping):
    import json
    host = _twice_interrupted(tmp_path, "restart_old", "missing")
    value = journal.pending(tmp_path)
    value["recovery_command_attempts"] = mapping
    (tmp_path / journal.FILE).write_text(json.dumps(value))
    before = (tmp_path / journal.FILE).read_bytes()
    with pytest.raises(journal.UpgradeStateError):
        recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    assert host.calls == [] and (tmp_path / journal.FILE).read_bytes() == before


def test_first_restart_request_in_a_later_attempt_is_durable_before_rpc(tmp_path, monkeypatch):
    host = _interrupted_candidate(tmp_path)
    record = journal.recovery_step

    def cut(directory, value, action, state, bound):
        result = record(directory, value, action, state, bound)
        if (action, state) == ("new_absent", "observed"):
            raise KeyboardInterrupt("synthetic cut before first restart request")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(journal, "recovery_step", cut)
        with pytest.raises(KeyboardInterrupt):
            recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    assert "restart_old" not in journal.pending(tmp_path)["recovery_command_attempts"]

    def effect(argv, context):
        assert context["action"] == "recover_restart_old_2"
        saved = journal.pending(tmp_path)
        assert saved["recovery_command_attempts"]["restart_old"] == 2
        assert {"action": "restart_old", "state": "requested"} in saved["recovery_actions"]
        _publish(tmp_path, context, spawned=False, exit_code=None, error="owner_lost")
        raise KeyboardInterrupt("synthetic no-spawn cut before ACK")

    host.with_effect = effect
    with pytest.raises(KeyboardInterrupt):
        recover(tmp_path, "aiport-mac", ready=lambda: True, run=host)
    del host.with_effect
    assert host.entries[OLD]["status"]["state"] == "stopped"
    assert recover(tmp_path, "aiport-mac", ready=lambda: True, run=host) == "recovered_old"
