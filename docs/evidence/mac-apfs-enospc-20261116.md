# Isolated Mac APFS disk-full boundary, 16 November 2026

Progress toward [deployment/recovery #24](https://github.com/Olli0103/unifi-protect-local-ai/issues/24)
and [instance lifecycle #45](https://github.com/Olli0103/unifi-protect-local-ai/issues/45).
Neither compound acceptance criterion is completed by this check.

## Exact scope

Source `31a2462e81cc4e826eb3257084eb673e53426439` contains the configuration-lock
error correction separately exercised on Linux in the
[isolated Linux disk-full record](config-lock-enospc-20261116.md).
All 183 application module hashes were frozen and checked unchanged after this
Mac exercise. Only invented controller addresses, cameras, identities and keys
were used. No production state, provider, model or camera was accessed.

A separately owned 128 MiB disk image was created through the current macOS
`diskutil image create blank` interface, formatted APFS and mounted at a private
fixture path. Observed filesystem capacity was 134,176,768 bytes. The probe wrote
129,499,136 bytes of its own bounded filler before the kernel returned
`ENOSPC` (errno 28). APFS still reported 3,166,208 available bytes: this record
claims actual refused allocation, not a zero-available-block count or a full
physical system disk.

Application socket creation and DNS were denied. Child-process admission allowed
only the existing OpenSSL tool for synthetic credential/certificate setup. The
Apple runtime adapter was explicitly synthetic; it did not invoke the actual
Apple Container daemon, PF helper, a privileged command or a network peer.

## Observed source/filesystem behavior

- Before filling, the ordinary Apple source reconciler completed synthetic
  create/start and persisted its real configuration, activation and host receipts.
- At actual APFS allocation failure, the shared atomic writer and the NAS and
  Apple validated receipt writers preserved their previous receipt bytes. No
  temporary receipt file remained.
- The complete Apple source apply path, supplied with a simulated stopped
  runtime, encountered two real receipt-write `ENOSPC` errors and refused with
  its existing uncertain-outcome error. The simulated prior runtime and all
  synthetic profile files remained unchanged; no simulated daemon mutation
  occurred. This is conservative refusal, not proof that a real daemon ran.
- Removing only the owned filler allowed ordinary durable publication and a
  subsequent source-level synthetic start to succeed. No unresolved receipt or
  activation guard was deleted to permit that start.
- There were zero application socket/DNS attempts. Source bytes were unchanged.
  The owned disk image was detached, and a fresh disk-image inventory confirmed
  no active attachment or remaining mount. The image and private result, source
  manifest, stdout/stderr and cleanup receipts are retained outside Git.

## Preparation failures retained

The first preparation could not list the existing Apple Container service because
its XPC connection was unavailable. It stopped before creating or attaching an
image. The service was not started or repaired. The separate filesystem scope
therefore does not claim a verified before/after inventory of real containers.

A second preparation used an older `hdiutil create -format` form, which the
installed macOS rejects for blank images. No source probe or mounted fixture
resulted. The current tool's help was read before using its supported blank-image
syntax. Both preparation failures remain separate from the one completed APFS
probe; they are not counted as successful fault tests.

## Limits

This is actual Mac APFS filesystem behavior with real source functions and a
synthetic runtime adapter, not an independent human review, actual native
container apply, adopted-device reconnect, native image installation, physical
host disk exhaustion, power loss, external billing reconciliation, or full
Mac Key/database/index restoration. The real container service's unavailable
baseline is not relabeled as a native lifecycle pass. No service, root policy,
network/address scope, productive pairing, alpha tag, release asset or image
visibility was changed. Broader lifecycle/recovery, quality and sustained-operation
requirements remain open.
