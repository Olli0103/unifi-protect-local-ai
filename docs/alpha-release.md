# First alpha delivery scope

The requested first alpha is **0.1.0a1** (`v0.1.0a1`). This document is a
release specification, not proof that its tag, images or release already exist.
Use the repository's [actual Releases](https://github.com/Olli0103/unifi-protect-local-ai/releases)
and the signed `release.json` for availability and exact immutable references.

## Deliverables

- Project source distribution and wheel, root Apache-2.0 license, original
  third-party notices, checksums, package/image inventories and standard
  GitHub OIDC/Sigstore provenance bundles.
- Default **AI Key** image for Linux AMD64 and Linux ARM64.
- Default **AI Port** image for Linux AMD64 and Linux ARM64.
- One multiarchitecture OCI index per profile. Docker selects its host
  architecture; Apple Container on supported Apple Silicon uses the **same
  Linux ARM64** image, not an unrelated macOS image or Apple VM state archive.

Proposed registry packages are
`ghcr.io/olli0103/local-aikey-0.1.0a1` and
`ghcr.io/olli0103/local-aiport-0.1.0a1`. These names are not existing
image/digest promises. The publisher creates attempt-specific tags such as
`0.1.0a1-arm64-runRUN_ID` and `0.1.0a1-index-runRUN_ID`, never a mutable `latest`.
Installation must use the verified profile/index digest from `release.json`.

## Excluded from this alpha

No model weights, vendor firmware, extracted vendor source, private protocol
traces, device identities/keys, camera media, production state or local VM image
is shipped. Optional detector/ONNX/OpenVINO build arguments and the separate
PostgreSQL/pgvector database image are outside the default-image distribution
review. A runtime dependency's source/notice duties are not waived because
models and optional profiles are excluded.

## Platform and feature boundaries

The native image CI builds both architectures without emulation and exercises
the default Key/Port installed-source, configuration refusal and state-reopen
cases. These checks do not prove all-camera inference, controller acceptance
on every firmware, field search quality or whole-host recovery.

The retained Mac observations use Apple Container 1.6.1 / Protect 7.4.96 and one
camera-free Port. Genuine adoption, clean recreation and an adopted-state
archive restore passed in that bounded case; see the
[exact tested host/guest subjects and limits](evidence/mac-adopted-state-restore-20261111.md).
That earlier guest image is not silently relabeled as this alpha's new image.
The other native multi-slot, camera, restart and sustained-operation requirements
remain open. ONVIF ingest is not implemented; face enrollment stays outside
this alpha qualification. Search has known unrelated-query false positives.

## Install only an actually published subject

1. Obtain the release's signed manifest and verify its source/digest/provenance
   through the [release verification procedure](releasing.md#verify-before-installation).
2. Copy the immutable AI Key or AI Port image reference from that verified
   manifest. With `IMAGE` set to that actual reference, fetch using
   `docker pull "$IMAGE"` or `container image pull "$IMAGE"` respectively.
3. Follow [Linux/NAS deployment](aiport-nas-compose.md) or the
   [Apple host actor procedure](aiport-apple-reconcile.md). Preserve private
   state separately; do not use example addresses, share identities or copy
   an existing adopted state into a second active container.
4. An image pull does not install Mac aliases, PF policy or the bounded
   privileged helper. Those are a separate, exact host setup, not root
   privileges embedded in the image. The alpha does not automatically migrate
   the existing production installation.

## Release prerequisites remain explicit

The owner's alpha publication request is recorded; it is not a new copyright,
firmware-rights or independent legal attestation. The
[issue #4 distribution review](legal/alpha-distribution-0.1.0a1.md) separates
retained technical evidence from missing review. The existing non-audit release
gate, exact source fingerprint, current-main seven-job CI, protected environments,
standard signatures and final provider readback all continue to apply to alphas.
A failed gate produces no public release; no empty alpha or example digest is
presented as an installable artifact.
