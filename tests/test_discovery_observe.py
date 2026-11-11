"""Only synthetic packets and loopback UDP responders; never real devices."""
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import threading

import pytest

from tools import discovery_observe as tool


def packet(fields):
    payload = b"".join(struct.pack(">BH", kind, len(value)) + value for kind, value in fields)
    return struct.pack(">BBH", 1, 0, len(payload)) + payload


def test_values_do_not_escape_structural_output():
    canary = ("synthetic-" + "must-not-be-printed").encode()
    wire = packet([(1, bytes.fromhex("020000000001")),
                   (2, socket.inet_aton("192.0.2.73")),
                   (11, canary), (153, b"arbitrary\x00value")])
    result = tool.parse_response(wire)
    text = json.dumps(result)
    assert result["header"] == {"version": 1, "command": 0, "length": len(wire) - 4}
    assert result["tlvs"] == [{"type": 1, "length": 6}, {"type": 2, "length": 4},
                             {"type": 11, "length": len(canary)}, {"type": 153, "length": 15}]
    for value in [canary.decode(), "192.0.2.73", "02:00:00:00:00:01", "arbitrary"]:
        assert value not in text
    assert set(result) == {"header", "tlvs"}


def test_all_truncations_fail_without_echoing_values():
    wire = packet([(11, ("synthetic-" + "hidden").encode())])
    for size in range(len(wire)):
        with pytest.raises(tool.ObservationError, match="^invalid_response$"):
            tool.parse_response(wire[:size])


@pytest.mark.parametrize("wire", [
    b"", b"\x01\x00\x00", b"\x02\x00\x00\x00", b"\x01\x04\x00\x00",
    b"\x01\x00\x00\x00trailing", b"\x01\x00\x00\x01\x01",
    b"\x01\x00\x00\x03\x01\x00\x01", b"x" * 65508,
])
def test_malformed_reply_is_rejected_with_fixed_category(wire):
    with pytest.raises(tool.ObservationError, match="^invalid_response$"):
        tool.parse_response(wire)


def test_empty_and_duplicate_fields_remain_metadata_only():
    result = tool.parse_response(packet([(3, b""), (3, b"abc")]))
    assert result["tlvs"] == [{"type": 3, "length": 0}, {"type": 3, "length": 3}]


def test_many_tlvs_cannot_generate_unbounded_output():
    tool.parse_response(packet([(3, b"")] * tool.MAX_FIELDS))
    with pytest.raises(tool.ObservationError, match="^invalid_response$"):
        tool.parse_response(packet([(3, b"")] * (tool.MAX_FIELDS + 1)))


@pytest.mark.parametrize("value", [
    "255.255.255.255", "0.0.0.0", "0.1.2.3", "233.89.188.1", "::1",
    "127.1", "localhost", "127.0.0.1\nsynthetic-canary", "127.0.0.999",
])
def test_invalid_target_is_rejected_before_socket_creation(monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid target must not open a socket")
    monkeypatch.setattr(tool.socket, "socket", forbidden)
    with pytest.raises(tool.ObservationError, match="^invalid_target$"):
        tool.observe(value)


def test_exactly_one_unicast_query_and_peer_are_used(monkeypatch):
    calls = []
    wire = packet([(11, b"synthetic-host")])

    class FakePeer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append(("closed",))

        def settimeout(self, value):
            calls.append(("timeout", value))

        def connect(self, address):
            calls.append(("connect", address))

        def send(self, value):
            calls.append(("send", value))
            return len(value)

        def recv(self, size):
            calls.append(("recv", size))
            return wire

    monkeypatch.setattr(tool.socket, "socket", lambda *args: FakePeer())
    assert tool.observe("192.0.2.73") == tool.parse_response(wire)
    assert calls == [("timeout", 3.0), ("connect", ("192.0.2.73", 10001)),
                     ("send", b"\x01\x00\x00\x00"), ("recv", 65508), ("closed",)]


def test_real_local_synthetic_udp_responder():
    wire = packet([(1, bytes.fromhex("020000000001")), (11, b"synthetic-host")])
    received = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(("127.0.0.1", 0))
        server.settimeout(3)
        def respond():
            request, peer = server.recvfrom(64)
            received.append(request)
            server.sendto(wire, peer)
        thread = threading.Thread(target=respond)
        thread.start()
        try:
            result = tool.observe("127.0.0.1", port=server.getsockname()[1])
        finally:
            thread.join(timeout=4)
        assert not thread.is_alive()
    assert received == [b"\x01\x00\x00\x00"]
    assert result == tool.parse_response(wire)


@pytest.mark.parametrize("failure,category", [
    (TimeoutError("synthetic-private-target"), "timeout"),
    (OSError("synthetic-private-target"), "network_error"),
])
def test_network_errors_never_echo_socket_exception(monkeypatch, capsys, failure, category):
    def failed(*args):
        raise failure
    monkeypatch.setattr(tool.socket, "socket", failed)
    assert tool.main(["--ip", "192.0.2.73"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == category + "\n"


def test_cli_prints_only_structural_metadata(monkeypatch, capsys):
    result = tool.parse_response(packet([(11, b"synthetic-private-host")]))
    monkeypatch.setattr(tool, "observe", lambda value: result)
    assert tool.main(["--ip", "192.0.2.73"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == result
    assert "192.0.2.73" not in captured.out
    assert "synthetic-private-host" not in captured.out


def test_actual_standalone_cli_rejects_non_ip_without_echoing_from_other_cwd(tmp_path):
    script = Path(tool.__file__).resolve()
    assert script == Path(__file__).resolve().parents[1] / "tools/discovery_observe.py"
    canary = "synthetic-" + "not-an-ip"
    result = subprocess.run([sys.executable, str(script), "--ip", canary],
                            cwd=tmp_path, env={}, capture_output=True, timeout=5)
    assert result.returncode == 1
    assert result.stdout == b""
    assert result.stderr == b"invalid_target\n"


def test_cli_argument_error_does_not_echo_unknown_arguments(capsys):
    with pytest.raises(SystemExit) as result:
        tool.main(["--unknown", "synthetic-private-value"])
    assert result.value.code == 2
    assert capsys.readouterr().err == "invalid_arguments\n"


def test_actual_standalone_cli_accepts_only_loopback_metadata(tmp_path):
    script = Path(tool.__file__).resolve()
    wire = packet([(11, b"synthetic-private-host"), (3, b"synthetic-version")])
    requests = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(("127.0.0.1", tool.DISCOVERY_PORT))
        server.settimeout(4)
        def respond():
            data, peer = server.recvfrom(64)
            requests.append(data)
            server.sendto(wire, peer)
        thread = threading.Thread(target=respond)
        thread.start()
        try:
            result = subprocess.run([sys.executable, str(script), "--ip", "127.0.0.1"],
                                    cwd=tmp_path, env={}, capture_output=True, timeout=5)
        finally:
            thread.join(timeout=5)
        assert not thread.is_alive()
    assert requests == [bytes((1, 0, 0, 0))]
    assert result.returncode == 0
    assert result.stderr == b""
    assert json.loads(result.stdout) == tool.parse_response(wire)
    for value in [b"127.0.0.1", b"synthetic-private-host", b"synthetic-version"]:
        assert value not in result.stdout + result.stderr


def test_connected_udp_socket_ignores_another_peer():
    correct = packet([(11, b"synthetic-host")])
    spoofed = packet([(1, b"synthetic-other"), (2, b"synthetic-other")])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(("127.0.0.1", 0))
        server.settimeout(3)
        def respond():
            _, peer = server.recvfrom(64)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
                other.bind(("127.0.0.1", 0))
                other.sendto(spoofed, peer)
            server.sendto(correct, peer)
        thread = threading.Thread(target=respond)
        thread.start()
        try:
            result = tool.observe("127.0.0.1", port=server.getsockname()[1])
        finally:
            thread.join(timeout=4)
        assert not thread.is_alive()
    assert result == tool.parse_response(correct)
