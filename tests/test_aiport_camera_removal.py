"""Reviewed camera removals and historical Protect event associations. Synthetic IDs only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from aikey import aiport_deployment as deployment
from test_aiport_deployment import camera, report


def cid(number):
    return f"{number:024x}"


def addressed(*numbers):
    return deployment.plan_ai_ports(report(*(camera(n) for n in numbers)),
                                    device_ips=[f"192.0.2.{n}" for n in (10, 11, 12, 13)])


def test_confirmed_removal_keeps_other_slots_and_reserves_empty_identity():
    old = addressed(1, 2, 3, 4, 5)
    inventory = report(*(camera(n) for n in (6, 5, 2, 1)))
    new = deployment.plan_ai_ports(inventory, previous_plan=old, removed_camera_ids=[cid(3), cid(4)])
    assert [(row["slot"], row["host_ip"], row["camera_ids"]) for row in new["instances"]] == [
        (1, "192.0.2.10", [cid(1), cid(2)]), (2, "192.0.2.11", []),
        (3, "192.0.2.12", [cid(5), cid(6)])]
    middle = new["instances"][1]
    assert middle["retired_camera_ids"] == [cid(3), cid(4)]
    assert middle["deployable"] is False and middle["reserved_capacity"] == "0"
    assert new["selected_camera_count"] == 4
    assert deployment.plan_ai_ports(inventory, previous_plan=new) == new
    assert deployment.plan_ai_ports(inventory, previous_plan=new, removed_camera_ids=[cid(3)]) == new
    later = deployment.plan_ai_ports(report(*(camera(n) for n in (7, 4, 6, 1, 2, 5))), previous_plan=new)
    assert [s["camera_ids"] for s in later["instances"]] == [
        [cid(1), cid(2)], [cid(4), cid(7)], [cid(5), cid(6)]]
    assert later["instances"][1]["retired_camera_ids"] == [cid(3)]
    assert later["instances"][1]["host_ip"] == middle["host_ip"]


def test_partial_and_last_removal_keep_identity_when_a_new_camera_uses_the_same_name():
    old = addressed(1, 2, 3)
    remaining = report(camera(4), camera(3), camera(2))
    for c in remaining["cameras"]:
        c["name"] = "Driveway"
    plan = deployment.plan_ai_ports(remaining, previous_plan=old, removed_camera_ids=[cid(1)])
    a, b = plan["instances"]
    assert a["camera_ids"] == [cid(2), cid(4)] and a["retired_camera_ids"] == [cid(1)]
    assert b == old["instances"][1]
    empty = deployment.plan_ai_ports(report(), previous_plan=plan, removed_camera_ids=[cid(i) for i in (2, 3, 4)])
    assert [(r["host_ip"], r["retired_camera_ids"]) for r in empty["instances"]] == [
        ("192.0.2.10", [cid(1), cid(2), cid(4)]), ("192.0.2.11", [cid(3)])]
    assert deployment.plan_ai_ports(report(), previous_plan=empty) == empty
    fresh = deployment.plan_ai_ports(report(camera(5)), previous_plan=empty)
    assert fresh["instances"][2]["camera_ids"] == [cid(5)] and fresh["instances"][2]["host_ip"] is None


@pytest.mark.parametrize("fault", ["offline", "present", "other_missing", "unknown", "duplicate", "no_previous"])
def test_confirmed_removal_refuses_ambiguous_inventory(fault):
    old = addressed(1, 2)
    rows = [camera(1)]
    removed = [cid(2)]
    if fault == "offline":
        rows.append(camera(2, processing_class="offline", state="DISCONNECTED"))
    elif fault == "present":
        rows.append(camera(2))
    elif fault == "other_missing":
        rows.clear()
    elif fault == "unknown":
        removed = [cid(9)]
    elif fault == "duplicate":
        removed *= 2
    elif fault == "no_previous":
        old = None
    original = deepcopy(old)
    with pytest.raises(deployment.AiPortPlanError):
        deployment.plan_ai_ports(report(*rows), previous_plan=old, removed_camera_ids=removed)
    assert old == original


def test_retired_identity_cannot_appear_on_two_slots():
    plan = deployment.plan_ai_ports(report(camera(2), camera(3)), previous_plan=addressed(1, 2, 3),
                                    removed_camera_ids=[cid(1)])
    plan["instances"][1]["retired_camera_ids"] = [cid(1)]
    with pytest.raises(deployment.AiPortPlanError):
        deployment.plan_ai_ports(report(camera(2), camera(3)), previous_plan=plan)


@pytest.mark.parametrize("fault", [None, "wrong_camera", "missing_event", "changed_times",
                                   "duplicate_event", "missing_removed_camera"])
def test_removal_cli_checks_historical_event_links_before_emitting_a_plan(tmp_path, capsys, fault):
    # The cameras have overlapping recording times, including the one being removed.
    before = [{"id": cid(i+10), "camera": cid(i), "start": 1000, "end": 2000} for i in (1, 2, 3)]
    after = list(reversed(deepcopy(before)))
    if fault == "wrong_camera":
        after[0]["camera"], after[1]["camera"] = after[1]["camera"], after[0]["camera"]
    elif fault == "missing_event":
        after.pop(0)
    elif fault == "changed_times":
        after[0]["end"] += 1
    elif fault == "duplicate_event":
        after.append(after[0])
    elif fault == "missing_removed_camera":
        before.pop(0)
        after.pop()
    files = [tmp_path / name for name in ("inventory.json", "previous.json", "before.json", "after.json")]
    for path, data in zip(files, (report(camera(3), camera(2)), addressed(1, 2, 3), before, after), strict=True):
        path.write_text(json.dumps(data))
    contents = [p.read_bytes() for p in files]
    args = ["--inventory", str(files[0]), "--previous-plan", str(files[1]), "--removed-camera-id", cid(1),
            "--check-recording-events", str(files[2]), str(files[3])]
    if fault:
        with pytest.raises(SystemExit) as exc:
            deployment.main(args)
        assert exc.value.code == 2
        output = capsys.readouterr()
        assert output.out == "" and "recording" in output.err.lower() and cid(1) not in output.err
    else:
        assert deployment.main(args) == 0
        plan = json.loads(capsys.readouterr().out)
        assert [(s["slot"], s["camera_ids"]) for s in plan["instances"]] == [(1, [cid(2)]), (2, [cid(3)])]
        assert plan["instances"][0]["retired_camera_ids"] == [cid(1)]
    assert [p.read_bytes() for p in files] == contents


def test_old_or_reordered_runtime_observation_cannot_remove_a_survivor():
    from aikey.aiport_rollout import observe_slot
    from test_aiport_rollout import CAM, bound_health
    config = {"mac": "02ABCDEF0011", "paired_streams": [{"camera_mac": c} for c in list(CAM.values())[:2]]}
    rows = [{"policy_enabled": True, "stream_points": 3}, {"policy_enabled": False, "stream_points": 5}]
    health = bound_health(config, rows)
    assert observe_slot(config, health)["paired"] == {CAM["Camera A"]}
    for bad in ({"pool_cameras": rows}, dict(health, pool_binding_schema="old"),
                dict(health, pool_cameras=[{}, {}])):
        assert observe_slot(config, bad)["paired"] is None and observe_slot(config, bad)["points"] == {}
    config["paired_streams"].reverse()
    assert observe_slot(config, health)["paired"] is None


def test_stale_review_of_two_unnamed_removals_cannot_edit_the_wrong_camera(tmp_path, monkeypatch):
    from aikey import aiport_rollout as rollout
    from test_aiport_rollout import _one_new_nas_slot, CAM, bound_health
    _, _, path, settings, _, _ = _one_new_nas_slot(tmp_path)
    path.write_text(json.dumps(settings))
    path.chmod(0o600)
    config_path = Path(settings["slots"][0]["state_dir"]) / "config.json"
    original = config_path.read_bytes()
    config = json.loads(original)
    inventory = report()
    paired = CAM["Camera A"]
    def health(*_):
        return bound_health(config, [{"policy_enabled": s["camera_mac"] == paired} for s in config["paired_streams"]])
    monkeypatch.setattr(rollout, "read_slot_health", health)
    first, _ = rollout.compute(settings, inventory)
    paired = CAM["Camera B"]
    other, _ = rollout.compute(settings, inventory)
    assert rollout.public(first) | {"revision": None} == rollout.public(other) | {"revision": None}
    with pytest.raises(rollout.PlanChanged):
        rollout.apply_if_current(path, inventory, first["revision"])
    assert config_path.read_bytes() == original


def test_apply_confirmed_removals_prunes_only_matching_permissions_and_keeps_the_port(tmp_path):
    from aikey import aiport_rollout as rollout
    from aikey.aiport_candidate import load_config
    from aikey.tls import ensure_identity_certificate
    from test_aiport_rollout import CAM, _provisioned, report as inventory, slot
    root, state = _provisioned(tmp_path)
    path = state / "config.json"
    initial = json.loads(path.read_text())
    a, b = CAM["Camera A"], CAM["Camera B"]
    ensure_identity_certificate(state, initial["mac"])
    identity = {p: p.read_bytes() for p in state.iterdir() if p != path}
    initial["live_pool_detector"].update(smart_types=["person"], provider_config={
        "provider": "openai", "model": "synthetic", "allow_remote": True,
        "base_url": "https://api.openai.com/v1", "max_output_tokens": 256},
        plate_cameras=[a], camera_thresholds={a: 0.7, b: 0.8})
    initial["live_speech_cameras"] = [a, b]
    path.write_text(json.dumps(initial))
    load_config(path, check_decoder_executable=False)
    slots = {"mac": slot("mac", initial["device_ip"], ["Camera A", "Camera B"], {"Camera B"})}
    plan = rollout.plan_rollout(inventory(drop=("Camera A", "Camera D", "Camera E")), slots)
    assert rollout.apply_rollout(plan, {"mac": state}, new_slot_parent=root, template_label="mac") == ["mac"]
    partial = load_config(path, check_decoder_executable=False)
    assert [s["camera_mac"] for s in partial["paired_streams"]] == [b]
    assert partial["live_speech_cameras"] == [b]
    assert partial["live_pool_detector"]["camera_thresholds"] == {b: 0.8}
    assert "plate_cameras" not in partial["live_pool_detector"]
    slots = {"mac": slot("mac", initial["device_ip"], ["Camera B"], set())}
    last = rollout.plan_rollout(report(), slots)
    assert rollout.apply_rollout(last, {"mac": state}, new_slot_parent=root, template_label="mac") == ["mac"]
    assert rollout.apply_rollout(last, {"mac": state}, new_slot_parent=root, template_label="mac") == []
    passive = load_config(path, check_decoder_executable=False)
    assert (passive["mac"], passive["device_ip"]) == (initial["mac"], initial["device_ip"])
    assert not ({"paired_streams", "live_speech_cameras", "live_pool_detector"} & passive.keys())
    assert rollout.observe_slot(passive, None)["allowlist"] == []
    assert json.loads((state / "config.json.before-rollout").read_text()) == initial
    assert all(p.read_bytes() == value for p, value in identity.items())


def test_nas_renders_and_admits_other_slots_without_touching_the_reserved_port(tmp_path):
    from aikey.aiport_nas_compose import NasComposeError, build_nas_compose
    from aikey.aiport_nas_reconcile import verify_inputs
    from test_aiport_nas_reconcile import inputs
    old, states, options, previous_manifest, inventory = inputs(tmp_path, selected_slot=2)
    reserved = Path(states[2]).parent / "slot-1"
    saved = {p: p.read_bytes() for p in reserved.iterdir() if p.is_file()}
    inventory["cameras"] = [inventory["cameras"][2]]
    new = deployment.plan_ai_ports(inventory, previous_plan=old, removed_camera_ids=[cid(1), cid(2)])
    assert build_nas_compose(new, states, **options) == previous_manifest
    assert verify_inputs(new, previous_manifest, inventory, states, options) == ["aiport_slot_2"]
    with pytest.raises(NasComposeError, match="retained empty slot"):
        build_nas_compose(new, states | {1: reserved}, **options)
    assert all(p.read_bytes() == value for p, value in saved.items())


async def test_exact_event_readback_after_middle_camera_is_removed(tmp_path, monkeypatch):
    from aiohttp import web
    from aikey.aiport_recording_links import verify_recording_links
    from test_native_camera_status import controller
    from test_index_native import index_session, authorized

    events = {cid(i+10): {"id": cid(i+10), "camera": cid(i), "start": 1000, "end": 2500} for i in (1, 2, 3)}
    reads = []
    async def get_event(request):
        authorized(request)
        eid = request.match_info["event"]
        reads.append(eid)
        return web.json_response(events[eid])

    route = web.get("/proxy/protect/api/events/{event}", get_event)
    async with controller(tmp_path, monkeypatch, additional_routes=[route]) as (reader, _, _):
        async with index_session(reader) as native:
            old = addressed(1, 2, 3)
            before = [await native.event(i) for i in events]
            new = deployment.plan_ai_ports(report(camera(3), camera(1)), previous_plan=old,
                                           removed_camera_ids=[cid(2)])
            after = [await native.event(i) for i in reversed(events)]
            verify_recording_links(old, new, before, after)
            events[cid(12)]["camera"] = cid(3)
            changed = [await native.event(i) for i in events]
            with pytest.raises(deployment.AiPortPlanError, match="recording"):
                verify_recording_links(old, new, before, changed)
    assert reads == [*events, *reversed(events), *events]


def test_three_distinct_recordings_still_play_by_their_original_camera_id(tmp_path):
    from aikey.aiport_recording_links import verify_recording_links
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg is needed to generate and decode the synthetic recordings")
    old = addressed(1, 2, 3)
    events = []
    for n, color in enumerate(("0xff0000", "0x00ff00", "0x0000ff"), 1):
        event = {"id": cid(n+10), "camera": cid(n), "start": 1000, "end": 2000}
        events.append(event)
        camera_dir = tmp_path / event["camera"]
        camera_dir.mkdir()
        subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        f"color=c={color}:s=32x32:r=2", "-t", "1", "-c:v", "mpeg4",
                        str(camera_dir / (event["id"] + ".mp4"))], check=True)

    def playback(plan, samples):
        owners = {cam: slot["slot"] for slot in plan["instances"]
                  for cam in slot["camera_ids"] + slot.get("retired_camera_ids", [])}
        result = {}
        for e in samples:
            clip = tmp_path / e["camera"] / (e["id"] + ".mp4")
            pixels = subprocess.check_output([ffmpeg, "-nostdin", "-v", "error", "-i", str(clip),
                                              "-pix_fmt", "rgb24", "-f", "rawvideo", "-threads", "1", "-"])
            assert len(pixels) == 2 * 32 * 32 * 3
            result[e["id"]] = (owners[e["camera"]], hashlib.sha256(pixels).digest())
        return result

    before = playback(old, events)
    new = deployment.plan_ai_ports(report(camera(3), camera(1)), previous_plan=old, removed_camera_ids=[cid(2)])
    after = list(reversed(events))
    verify_recording_links(old, new, events, after)
    assert len({frames for _, frames in before.values()}) == 3
    assert playback(new, after) == before


def test_ambiguous_native_pairings_and_passive_slot_diff(tmp_path):
    from aikey.aiport_slot_diff import SlotDiffError, diff_slots, apply_allowlist
    from test_aiport_rollout import _provisioned
    from test_aiport_slot_diff import cameras, aiports, A, B, MAC
    _, state = _provisioned(tmp_path)
    config = json.loads((state / "config.json").read_text())
    for row, camera_id in zip(config["paired_streams"], (A, B), strict=True):
        row["camera_mac"] = MAC[camera_id]
    ports = aiports()
    ports[0]["mac"] = config["mac"]
    ports[0]["pairedCameras"] = []
    current = {"mac": config}
    plan = diff_slots(current, ports, cameras())
    edited = apply_allowlist(current, plan)
    assert edited["mac"]["mac"] == config["mac"] and "paired_streams" not in edited["mac"]
    assert not any(a["action"] == "remove_from_allowlist" for a in diff_slots(edited, ports, cameras())["actions"])
    ports[0]["pairedCameras"] = [B]
    with pytest.raises(SlotDiffError, match="Ambiguous"):
        diff_slots(current, ports, cameras())


def test_live_rollout_reserves_an_offline_camera_even_if_its_model_is_unavailable():
    from aikey.aiport_rollout import plan_rollout
    from test_aiport_rollout import current, report as inventory
    observed = current()
    data = inventory(offline=("Camera B",))
    b = next(r for r in data["cameras"] if r["name"] == "Camera B")
    b.update(model=None, processing_class="offline")
    observed["mac"]["paired"].discard(b["mac"])
    planned = plan_rollout(data, observed)
    assert b["mac"] in planned["slots"]["mac"]["keep"]
    assert not planned["slots"]["mac"]["remove"]
