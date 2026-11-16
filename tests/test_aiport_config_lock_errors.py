"""Operation I/O errors must not be mistaken for lock-acquisition failures."""
import errno
import fcntl
import os

import pytest

import aikey.aiport_config_store as port
from test_aiport_config_store import fixture


@pytest.mark.parametrize("number", [errno.ENOSPC, errno.EIO, errno.EROFS])
def test_operation_io_error_retains_exact_identity_errno_and_releases_lock(tmp_path, number):
    store, path, _ = fixture(tmp_path)
    before = path.read_bytes()
    failure = OSError(number, "synthetic operation failure")
    with pytest.raises(OSError) as raised:
        with store._locked(allow_device_pending=True, allow_host_pending=True):
            raise failure
    assert raised.value is failure
    assert raised.value.errno == number
    assert path.read_bytes() == before
    # A separate descriptor must acquire the real kernel lock after failure.
    with store.lock_path.open("rb") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def test_normal_body_keeps_real_exclusive_lock_until_exit(tmp_path):
    store, path, _ = fixture(tmp_path)
    before = path.read_bytes()
    with store._locked(allow_device_pending=True, allow_host_pending=True):
        with store.lock_path.open("rb") as competing:
            with pytest.raises(BlockingIOError):
                fcntl.flock(competing.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    with store.lock_path.open("rb") as competing:
        fcntl.flock(competing.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(competing.fileno(), fcntl.LOCK_UN)
    assert path.read_bytes() == before


@pytest.mark.parametrize("stage", ["open", "metadata", "acquire"])
def test_actual_lock_setup_error_remains_fixed_and_closes_descriptor(tmp_path, monkeypatch, stage):
    store, path, _ = fixture(tmp_path)
    before = path.read_bytes()
    failure = OSError(errno.EACCES, "synthetic lock setup failure")
    real_open, real_fchmod = port.os.open, port.os.fchmod
    descriptors = []
    reached = []
    def selected_open(target, *args, **kwargs):
        if target == store.lock_path:
            if stage == "open":
                raise failure
            descriptor = real_open(target, *args, **kwargs)
            descriptors.append(descriptor)
            return descriptor
        return real_open(target, *args, **kwargs)
    def selected_fchmod(descriptor, mode):
        if stage == "metadata" and descriptor in descriptors:
            raise failure
        return real_fchmod(descriptor, mode)
    def refuse_acquire(descriptor):
        assert stage == "acquire"
        raise failure
    with monkeypatch.context() as patch:
        patch.setattr(port.os, "open", selected_open)
        patch.setattr(port.os, "fchmod", selected_fchmod)
        if stage == "acquire":
            patch.setattr(port, "acquire_file_lock", refuse_acquire)
        with pytest.raises(port.AiPortConfigurationError,
                           match="^aiport_config_lock_unavailable$") as raised:
            with store._locked(allow_device_pending=True, allow_host_pending=True):
                reached.append(True)
    assert raised.value.__cause__ is failure
    assert not reached
    for descriptor in descriptors:
        with pytest.raises(OSError) as closed:
            os.fstat(descriptor)
        assert closed.value.errno == errno.EBADF
    assert path.read_bytes() == before
    with store._locked(allow_device_pending=True, allow_host_pending=True):
        pass
