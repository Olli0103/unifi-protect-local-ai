# Configuration lock errors and isolated Linux disk full, 16 November 2026

Progress toward [deployment/recovery #24](https://github.com/Olli0103/unifi-protect-local-ai/issues/24)
and [instance lifecycle #45](https://github.com/Olli0103/unifi-protect-local-ai/issues/45).
Neither original issue is completed by this narrow check.

## Reproduced failure and correction

Baseline source `f4c1adef4f69c5b451b758819b26ff6f6f25c077` safely refused a
NAS reconciliation recipe write at actual Linux `ENOSPC`, before any daemon
operation. However, the configuration-store context manager incorrectly
converted that protected-operation error into `aiport_config_lock_unavailable`.
The failed attempt and its successful cleanup are retained, not counted as a PASS.

The correction preserves an operation's original `OSError` once the protected
body starts. Lock opening, metadata checks and acquisition still use the fixed
lock-error classification. No automatic retry, policy bypass or state repair
is added. Mutual exclusion, pending device/host checks and descriptor cleanup
remain in place. The corrected module SHA-256 is
`717ab29ea5be04133895188ba1c79b622874cd9fa7c255bdd377e2919373c9f4`.

## Source regressions

Seven cases exercise the actual context manager:

- `ENOSPC`, `EIO` and `EROFS` preserve the exact exception object and errno,
  leave configuration bytes unchanged, and release the actual kernel lock.
  All three fail on the baseline above.
- A normal protected body holds the exclusive lock; another descriptor cannot
  acquire it until exit.
- Open, metadata and acquisition errors retain their fixed classification and
  original cause, never enter the body, close owned descriptors and permit a
  later successful operation.

The four lock/setup controls already pass on baseline. The corrected seven
cases plus the configuration, activation, NAS and Apple reconciliation group
pass **113 tests**. Whole-tree Ruff and the audit-only source check pass; the
latter explicitly reports `release_approved=false`, not a new release approval.

## Public-operation failure boundary

The first full-suite run exposed one old assertion that expected any journal
write failure to become a configuration error through the overbroad lock wrapper.
That expectation is updated to the intended original `OSError`/errno contract;
its existing committed-configuration and unavailable-undo assertions remain.
A new actual-journal HTTP case confirms a redacted uncertain response, preserved
committed settings, no fabricated undo and refusal of the spent confirmation
without a second journal attempt. The combined lock and camera-threshold
source/HTTP group passes **63 tests**. This does not convert the earlier full
run's failure into a pass; the complete corrected suite is a separate result.

## Actual isolated Linux filesystem check

One synthetic fixture uses a real 1 MiB tmpfs, network none and a read-only
root filesystem, without a Docker socket or production state mount. All 183
application modules plus the harness are hash-verified; the only source overlay
is the corrected module above. The unchanged probe fills its own filesystem
until the kernel returns errno 28.

Observed corrected result:

- Positive admission reaches the explicit no-daemon spy before filling the
  filesystem, excluding an unrelated preexisting input rejection.
- Existing atomic and validated receipt bytes survive the failed write.
- The complete NAS execute path refuses before any daemon invocation;
  daemon calls and socket attempts both remain zero.
- Synthetic identity files remain unchanged; removing only the owned filler
  permits a subsequent write.
- The fixture is removed and its absence is checked again. All **80 preexisting
  containers** have identical recorded IDs, images, PIDs, states and restart
  counts before and after, in both the failed and corrected attempts.

Private intent, frozen inputs, result, before/after comparisons and complete
stdout/stderr are retained outside the public repository. No private identifiers,
credentials, infrastructure paths or media are published. No production source,
container, image, camera, provider or model setting was changed.

## Explicit limits

This is same-agent source/fixture evidence on an actual Linux tmpfs, not an
independent human review. It is not a full physical host disk failure, Mac
filesystem ENOSPC, power-loss recovery, native Port creation/adoption, new
camera-slot scaling/removal, external billing reconciliation or sustained
operation. Those original acceptance gaps remain open. Existing alpha tags,
release assets/signatures and private container visibility are unchanged.
