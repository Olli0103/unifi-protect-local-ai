"""One explicit owned-device discovery query; output structural metadata only.

No scan, broadcast, multicast, firmware access, response-value logging or files.
The operator supplies an owned device IPv4. A successful response is a bounded
observation of that device, not proof of AI Key/AI Port compatibility or rights.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import struct
import sys

DISCOVERY_PORT = 10001
TIMEOUT_SECONDS = 3.0
MAX_FIELDS = 256
QUERY = bytes((1, 0, 0, 0))
_HEADER = struct.Struct(">BBH")
_TLV = struct.Struct(">BH")


class ObservationError(ValueError):
    """Only fixed error categories may be shown to the operator."""


def parse_response(data: bytes) -> dict:
    if not isinstance(data, bytes) or not 4 <= len(data) <= 65507:
        raise ObservationError("invalid_response")
    version, command, length = _HEADER.unpack_from(data)
    if version != 1 or command != 0 or length != len(data) - 4:
        raise ObservationError("invalid_response")
    fields = []
    offset = 4
    while offset < len(data):
        if len(fields) >= MAX_FIELDS:
            raise ObservationError("invalid_response")
        if len(data) - offset < _TLV.size:
            raise ObservationError("invalid_response")
        kind, size = _TLV.unpack_from(data, offset)
        offset += _TLV.size
        if size > len(data) - offset:
            raise ObservationError("invalid_response")
        fields.append({"type": kind, "length": size})
        offset += size
    return {"header": {"version": version, "command": command, "length": length},
            "tlvs": fields}


def validate_target(value: str) -> str:
    try:
        target = ipaddress.IPv4Address(value)
    except (ValueError, TypeError):
        raise ObservationError("invalid_target") from None
    if (target.is_unspecified or target.is_multicast or target.is_reserved
            or int(target) == 0xFFFFFFFF or target.packed[0] == 0):
        raise ObservationError("invalid_target")
    return str(target)


def observe(value: str, *, port: int = DISCOVERY_PORT) -> dict:
    target = validate_target(value)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as peer:
            # SO_BROADCAST remains disabled. A connected UDP socket only accepts
            # replies from the one explicitly selected peer/port.
            peer.settimeout(TIMEOUT_SECONDS)
            peer.connect((target, port))
            peer.send(QUERY)
            data = peer.recv(65508)
    except TimeoutError:
        raise ObservationError("timeout") from None
    except OSError:
        raise ObservationError("network_error") from None
    return parse_response(data)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error may echo an entered address or other value.
        self.exit(2, "invalid_arguments\n")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--ip", required=True, metavar="OWNED_DEVICE_IPV4")
    args = parser.parse_args(argv)
    try:
        result = observe(args.ip)
    except ObservationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
