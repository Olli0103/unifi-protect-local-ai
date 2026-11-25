"""Read-only capacity and listener plan for an independent AI Port profile.

This module does not claim an adopted device, pair cameras, or open sockets.
Its conservative capacity limits follow the published AI Port FAQ. For exact
known Protect models, published maximum pixels bound an unknown recording
resolution; other unknown models reserve maximum capacity.
"""

from __future__ import annotations

import argparse
import asyncio
from fractions import Fraction
import ipaddress
import json
from pathlib import Path
import re

from .aiport_ingest import stream_capacity_points
from .camera_inventory import InventoryError, fetch_inventory


AI_KEY_MANAGEMENT_PORT = 8080
AI_PORT_MANAGEMENT_PORT = 443
AI_PORT_CONTAINER_PORT = 8443
AI_PORT_DISCOVERY_PORT = 10001
AI_PORT_CONTROLLER_WS_PORT = 7442
AI_PORT_PROTECT_RTSP_PORT = 7447
ONVIF_BLOCKER = "onvif_ingest_not_implemented"
_CAMERA_ID = re.compile(r"[0-9a-fA-F]{24}\Z")
_G3_G5_MODEL = re.compile(r"UVC G[345](?:\s|\Z)")
_SCOPES = frozenset({"legacy-only", "legacy-and-g3-g5"})
_CAPACITY = {
    "protect": {"HD": Fraction(1, 5), "2K": Fraction(1, 3),
                "4K": Fraction(1, 2), None: Fraction(1, 2)},
    "onvif": {"HD": Fraction(1, 3), "2K": Fraction(1, 2),
              "4K": Fraction(1), None: Fraction(1)},
}
# Exact Protect model names and published camera maximums. These dimensions
# bound a missing recording resolution; they are not a claim about the current
# stream. The live ingress independently enforces its ten-point limit.
_PROTECT_MODEL_MAX_PIXELS = {
    "UVC G3 Instant": (1920, 1080),
    "UVC G4 Instant": (2688, 1512),
    "UVC G4 Pro": (3840, 2160),
    "UVC G4 Bullet": (2688, 1512),
    "UVC G4 Dome": (2688, 1512),
    "UVC G5 Flex": (2688, 1512),
    # Main-lens channel 0 that Protect 7.3.68 streams to a paired AI Port
    # (Camera E, 26 Sep 2026); without it the doorbell counted as 4K.
    "UVC G4 Doorbell Pro": (1600, 1200),
}


class AiPortPlanError(ValueError):
    """The supplied inventory or address pool cannot form a safe plan."""


def _ip(value: str) -> str:
    if not isinstance(value, str):
        raise AiPortPlanError("A concrete IPv4 address is required")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise AiPortPlanError("A concrete IPv4 address is required") from exc
    if (address.is_unspecified or address.is_multicast or address.is_loopback
            or int(address) == 0xFFFFFFFF):
        raise AiPortPlanError("A reachable unicast LAN address is required")
    return str(address)


def _eligible(report: dict, camera_scope: str) -> tuple[
        dict[str, list[tuple[str, str | None, Fraction]]], int, int]:
    if (not isinstance(report, dict) or report.get("schema") != "aikey-camera-preflight/1"
            or not isinstance(report.get("cameras"), list)
            or len(report["cameras"]) > 256):
        raise AiPortPlanError("A complete camera preflight v1 report is required")
    groups: dict[str, list[tuple[str, str | None, Fraction]]] = {"protect": [], "onvif": []}
    seen = set()
    legacy_count = 0
    enhancement_count = 0
    for row in report["cameras"]:
        if not isinstance(row, dict):
            raise AiPortPlanError("Invalid camera row")
        camera_id = row.get("id")
        if not isinstance(camera_id, str) or not _CAMERA_ID.fullmatch(camera_id) or camera_id.lower() in seen:
            raise AiPortPlanError("Invalid or duplicate camera ID")
        seen.add(camera_id.lower())
        processing_class = row.get("processing_class")
        if processing_class not in {"legacy_ingress_needed", "smart_event_candidate", "offline"}:
            raise AiPortPlanError("Unknown camera processing class")
        is_legacy = processing_class == "legacy_ingress_needed"
        is_enhancement = (camera_scope == "legacy-and-g3-g5"
                          and processing_class == "smart_event_candidate"
                          and row.get("source_kind") in (None, "protect")
                          and isinstance(row.get("model"), str)
                          and _G3_G5_MODEL.match(row["model"]) is not None)
        if not (is_legacy or is_enhancement):
            continue
        if row.get("state") != "CONNECTED":
            raise AiPortPlanError("Selected camera is not connected")
        source = row.get("source_kind")
        if source is None and isinstance(row.get("model"), str) and row["model"].startswith("UVC "):
            source = "protect"
        if source not in _CAPACITY:
            raise AiPortPlanError("Legacy camera source is unknown; Protect and ONVIF cannot share an AI Port")
        resolution = row.get("recording_resolution")
        if resolution not in _CAPACITY[source]:
            raise AiPortPlanError("Camera resolution must be HD, 2K, 4K or unknown")
        weight = _CAPACITY[source][resolution]
        if resolution is None and source == "protect":
            maximum = _PROTECT_MODEL_MAX_PIXELS.get(row.get("model"))
            if maximum is not None:
                weight = Fraction(stream_capacity_points(*maximum), 10)
        groups[source].append((camera_id, resolution, weight))
        legacy_count += int(is_legacy)
        enhancement_count += int(is_enhancement)
    return groups, legacy_count, enhancement_count


def _slot_camera_ids(item: dict, assigned: set[str]) -> tuple[list[str], list[str]]:
    active, retired = item.get("camera_ids"), item.get("retired_camera_ids", [])
    if not isinstance(active, list) or not isinstance(retired, list) or not (active or retained_empty_slot(item)):
        raise AiPortPlanError("Invalid previous AI Port slot")
    for camera in active + retired:
        if not isinstance(camera, str) or not _CAMERA_ID.fullmatch(camera) or camera.lower() in assigned:
            raise AiPortPlanError("Invalid or duplicate previous camera assignment")
        assigned.add(camera.lower())
    return active, retired


def _previous_slots(previous_plan: dict | None,
                    selected: dict[str, tuple[str, str | None, Fraction]],
                    addresses: list[str], key_address: str | None, removed: set[str]
                    ) -> tuple[list[dict], str | None]:
    if previous_plan is None:
        if removed:
            raise AiPortPlanError("A confirmed camera removal requires its previous plan")
        return [], key_address
    if (not isinstance(previous_plan, dict)
            or previous_plan.get("schema") != "aikey-aiport-deployment-plan/2"
            or not isinstance(previous_plan.get("instances"), list)
            or len(previous_plan["instances"]) > 256
            or not isinstance(previous_plan.get("ai_key"), dict)):
        raise AiPortPlanError("A previous AI Port deployment plan v2 is required")
    previous_key = previous_plan["ai_key"].get("host_ip")
    if previous_key is not None:
        previous_key = _ip(previous_key)
    if key_address is not None and previous_key is not None and key_address != previous_key:
        raise AiPortPlanError("The existing AI Key address cannot move during reconciliation")
    key_address = key_address or previous_key
    bins: list[dict] = []
    assigned: set[str] = set()
    current_ids = {key.lower() for key in selected}
    for index, item in enumerate(previous_plan["instances"]):
        if (not isinstance(item, dict) or type(item.get("slot")) is not int
                or item["slot"] != index + 1
                or item.get("source_kind") not in _CAPACITY):
            raise AiPortPlanError("Invalid previous AI Port slot")
        host_ip = item.get("host_ip")
        if host_ip is not None:
            host_ip = _ip(host_ip)
        if index < len(addresses) and host_ip is not None and addresses[index] != host_ip:
            raise AiPortPlanError("An existing AI Port address cannot move during reconciliation")
        source = item["source_kind"]
        cameras = []
        history = []
        load = Fraction()
        active, retired = _slot_camera_ids(item, assigned)
        historical = set(retired)
        for camera_id in active + retired:
            identity = camera_id.lower()
            current = selected.get(camera_id)
            if identity in removed or (camera_id in historical and identity not in current_ids):
                history.append(camera_id)
                continue
            if current is None or current[0] != source:
                raise AiPortPlanError("A previously assigned camera changed or is unavailable; review its pairing")
            _, resolution, weight = current
            load += weight
            cameras.append({"id": camera_id, "recording_resolution": resolution})
        if load > 1:
            raise AiPortPlanError("An existing AI Port slot exceeds current camera capacity")
        bins.append({"source_kind": source, "load": load,
                     "cameras": cameras, "host_ip": host_ip, "retired_camera_ids": sorted(history)})
    if not removed <= assigned:
        raise AiPortPlanError("A confirmed removal must belong to a previous AI Port slot")
    return bins, key_address


def retained_empty_slot(slot: dict) -> bool:
    """An idle slot keeps its address and historical camera ownership."""
    if not isinstance(slot, dict):
        return False
    retired = slot.get("retired_camera_ids")
    return (slot.get("camera_ids") == [] and isinstance(retired, list) and bool(retired)
            and all(isinstance(i, str) and _CAMERA_ID.fullmatch(i) for i in retired)
            and slot.get("blocked_by") == "retained_empty_slot" and slot.get("deployable") is False
            and slot.get("reserved_capacity") == "0" and slot.get("resolution_unverified") is False)


def plan_ai_ports(report: dict, *, device_ips: list[str] | None = None,
                  ai_key_ip: str | None = None,
                  camera_scope: str = "legacy-only",
                  previous_plan: dict | None = None,
                  removed_camera_ids: list[str] | tuple[str, ...] = ()) -> dict:
    """Size independent AI Port instances without pairing or opening ports.

    Each instance gets a different host IP because the management listener is
    fixed to 443. A single host UDP 10001 responder may cover all identities.
    """
    if camera_scope not in _SCOPES:
        raise AiPortPlanError("Unknown camera scope")
    groups, legacy_count, enhancement_count = _eligible(report, camera_scope)
    if (not isinstance(removed_camera_ids, (list, tuple))
            or any(not isinstance(i, str) or not _CAMERA_ID.fullmatch(i) for i in removed_camera_ids)):
        raise AiPortPlanError("Invalid confirmed camera removal")
    removed = {i.lower() for i in removed_camera_ids}
    if len(removed) != len(removed_camera_ids) or any(row["id"].lower() in removed for row in report["cameras"]):
        raise AiPortPlanError("Confirmed removals must be unique and absent from the complete inventory")
    selected = {camera_id: (source, resolution, weight)
                for source, cameras in groups.items()
                for camera_id, resolution, weight in cameras}
    addresses = [_ip(value) for value in (device_ips or [])]
    if len(set(addresses)) != len(addresses):
        raise AiPortPlanError("AI Port addresses must be distinct")
    key_address = _ip(ai_key_ip) if ai_key_ip is not None else None
    allocations, key_address = _previous_slots(previous_plan, selected,
                                                addresses, key_address, removed)
    assigned = {camera["id"] for item in allocations for camera in item["cameras"]}
    for source in ("protect", "onvif"):
        for camera_id, resolution, weight in sorted(groups[source], key=lambda item: (-item[2], item[0])):
            if camera_id in assigned:
                continue
            destination = next((item for item in allocations
                                if item["cameras"] and item["source_kind"] == source
                                and item["load"] + weight <= 1), None)
            if destination is None:
                destination = {"source_kind": source, "load": Fraction(), "cameras": []}
                allocations.append(destination)
            destination["load"] += weight
            destination["cameras"].append({"id": camera_id, "recording_resolution": resolution})
            assigned.add(camera_id)
    instances = []
    for index, allocation in enumerate(allocations):
        address = addresses[index] if index < len(addresses) else allocation.get("host_ip")
        blocker = ONVIF_BLOCKER if allocation["source_kind"] == "onvif" else None
        if not allocation["cameras"]:
            blocker = "retained_empty_slot"
        instances.append({
            "slot": index + 1,
            "source_kind": allocation["source_kind"],
            "camera_ids": [camera["id"] for camera in allocation["cameras"]],
            **({"retired_camera_ids": allocation["retired_camera_ids"]}
               if allocation.get("retired_camera_ids") else {}),
            "resolution_unverified": any(camera["recording_resolution"] is None
                                         for camera in allocation["cameras"]),
            "reserved_capacity": str(allocation["load"]),
            "host_ip": address,
            "management_tcp": AI_PORT_MANAGEMENT_PORT,
            "apple_publish": (f"{address}:443:{AI_PORT_CONTAINER_PORT}/tcp" if address else None),
            "state": "planned_only",
            # The ingest accepts only Protect's RTSP relay (port 7447 on the
            # controller). An ONVIF camera streams from its own address and
            # port, which no slot can decode yet, so ONVIF capacity is planned
            # but not deployed (#28).
            "deployable": blocker is None,
            **({"blocked_by": blocker} if blocker else {}),
        })
    assigned_addresses = [item["host_ip"] for item in instances if item["host_ip"]]
    if (len(set(assigned_addresses)) != len(assigned_addresses)
            or key_address in assigned_addresses):
        raise AiPortPlanError("AI Port and AI Key require distinct host addresses")
    return {
        "schema": "aikey-aiport-deployment-plan/2",
        "camera_scope": camera_scope,
        "legacy_camera_count": legacy_count,
        "enhancement_camera_count": enhancement_count,
        "selected_camera_count": legacy_count + enhancement_count,
        "ai_port_instances_required": len(instances),
        "ai_port_instances_without_address": sum(item["host_ip"] is None for item in instances),
        "ai_key": {"host_ip": key_address, "management_tcp": AI_KEY_MANAGEMENT_PORT},
        "host_discovery_udp": AI_PORT_DISCOVERY_PORT if instances else None,
        "controller_websocket_tcp": AI_PORT_CONTROLLER_WS_PORT if instances else None,
        "instances": instances,
        "adoption": "needs_evidence",
        "camera_pairing": "disabled",
        "camera_stream_ports": {
            "protect_outbound_tcp": ([AI_PORT_PROTECT_RTSP_PORT]
                                     if groups["protect"] else []),
            "onvif_outbound_tcp": "needs_evidence" if groups["onvif"] else [],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan AI Port capacity and fixed listeners from a private camera preflight")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--inventory", type=Path, help="Existing private camera preflight JSON")
    source.add_argument("--controller", help="Fetch the current Protect inventory from this private IPv4 host")
    parser.add_argument("--previous-plan", type=Path,
                        help="Preserve existing camera slots and host addresses")
    parser.add_argument("--removed-camera-id", action="append", default=[],
                        help="Confirm a previously assigned camera is absent from the inventory (repeatable)")
    parser.add_argument("--check-recording-events", nargs=2, type=Path, metavar=("BEFORE", "AFTER"),
                        help="Check private native event samples against both plans before emitting the new plan")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--web-trust-file", type=Path)
    parser.add_argument("--web-cert-file", type=Path)
    parser.add_argument("--ai-port-ip", action="append", default=[])
    parser.add_argument("--ai-key-ip")
    parser.add_argument("--camera-scope", choices=sorted(_SCOPES),
                        default="legacy-only")
    args = parser.parse_args(argv)
    if args.controller:
        if not all((args.api_key_file, args.web_trust_file, args.web_cert_file)):
            parser.error("Live inventory requires private API-key, web-trust and web-certificate files")
    elif any((args.api_key_file, args.web_trust_file, args.web_cert_file)):
        parser.error("Protect credential files are only used with --controller")
    try:
        if args.controller:
            report = asyncio.run(fetch_inventory(args.controller, api_key_file=args.api_key_file,
                                                  trust_file=args.web_trust_file,
                                                  cert_file=args.web_cert_file))
        else:
            report = json.loads(args.inventory.read_text())
        previous_plan = (json.loads(args.previous_plan.read_text())
                         if args.previous_plan else None)
        plan = plan_ai_ports(report, device_ips=args.ai_port_ip,
                             ai_key_ip=args.ai_key_ip,
                             camera_scope=args.camera_scope,
                             previous_plan=previous_plan, removed_camera_ids=args.removed_camera_id)
        if args.check_recording_events:
            from .aiport_recording_links import verify_recording_links
            if previous_plan is None:
                raise AiPortPlanError("Checking recording links requires a previous plan")
            verify_recording_links(previous_plan, plan, *[
                json.loads(path.read_text()) for path in args.check_recording_events])
    except (OSError, json.JSONDecodeError, AiPortPlanError, InventoryError) as exc:
        parser.error(str(exc))
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
