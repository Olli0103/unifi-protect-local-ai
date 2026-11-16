# Alpha 0.1.0a1: delivery, verification and limits

**Published on 16 November 2026:**
[GitHub prerelease v0.1.0a1](https://github.com/Olli0103/unifi-protect-local-ai/releases/tag/v0.1.0a1).
[Run 43920818331](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43920818331)
completed successfully after the owner's final `release` approval. The original
release ID is `444049704`; 25 uploaded assets have matching provider SHA-256
readbacks. This is an experimental alpha, not a stable/support guarantee.

## Exact published subjects

- Artifact source/tag: `a3da9c21715dade37fbe3a25529fa85fd17dc430` / `v0.1.0a1`.
- Executing recovery policy: `18f0ebd695ceccae861daed8c02aff1eba1aed9c`.
  The signed manifest binds this policy and run to the unchanged artifact source.
- [`release.json`](https://github.com/Olli0103/unifi-protect-local-ai/releases/download/v0.1.0a1/release.json)
  SHA-256: `0d7b28aaef155c43277d5129a9fe40369ff58213dc7ab63941f63111e6333eb3`.
- [`SHA256SUMS`](https://github.com/Olli0103/unifi-protect-local-ai/releases/download/v0.1.0a1/SHA256SUMS)
  SHA-256: `06f794bf929bf80579fe1aebfcb1e6b9c2ba8450bee2e20fc357fdadad289658`.
  It lists 22 normal assets; `release.json` also binds that checksum file, and
  root Sigstore provenance binds the manifest/checksums without circular hashing.
- Native AMD64/ARM64 installed-source/state cases, cleanup, upstream/root
  signatures and the actual final consumer against this candidate passed.
  These results do not substitute for native Protect or independent-user tests.

**Container images remain private.** Successful source/package publication did
not change GHCR visibility and does not prove anonymous pulls. The exact signed
multiarchitecture subjects are:

| Profile | Immutable reference, requiring authorized registry access |
| --- | --- |
| AI Key | `ghcr.io/olli0103/local-aikey-0.1.0a1@sha256:8fd0700e189859354c5f80c7a5dbebbdf7d554825adfdc31901ac543ed9224e8` |
| AI Port | `ghcr.io/olli0103/local-aikey-0.1.0a1@sha256:eb09a6ac4a58c194e427f40066fada3568859c0b32b6aa57e27aa811634422a9` |

Both indices cover `linux/amd64` and `linux/arm64`. Separate profile identities
share this existing versioned package under the
[bounded private-registry recovery](legal/private-registry-recovery.md); do not
substitute a guessed `local-aiport-0.1.0a1` package or a mutable tag.
Use the signed manifest and [verification procedure](releasing.md#verify-before-installation),
not this table alone, before installation. Post-release documentation is not
retroactively part of the tagged alpha source.

## Deliverables

- Project source distribution and wheel, root Apache-2.0 license, original
  third-party notices, checksums, package/image inventories and standard
  GitHub OIDC/Sigstore provenance bundles.
- Default **AI Key** image for Linux AMD64 and Linux ARM64.
- Default **AI Port** image for Linux AMD64 and Linux ARM64.
- One multiarchitecture OCI index per profile. Docker selects its host
  architecture; Apple Container on supported Apple Silicon uses the **same
  Linux ARM64** image, not an unrelated macOS image or Apple VM state archive.

For this recovery, profile-specific tags are
`<profile>-0.1.0a1-<amd64|arm64|index>-run43920818331` in the shared package
above, never a mutable `latest`. Other release layouts must follow their own
verified manifest. Installation must use the verified profile/index digest from
`release.json`, not the name of a CI artifact.

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
   manifest. The images are private: an anonymous pull is not expected to work.
   With authorized registry access and `IMAGE` set to that actual reference,
   fetch using `docker pull "$IMAGE"` or `container image pull "$IMAGE"`
   respectively. Without that access, use the [source-build guide](deployment.md).
3. Follow [Linux/NAS deployment](aiport-nas-compose.md) or the
   [Apple host actor procedure](aiport-apple-reconcile.md). Preserve private
   state separately; do not use example addresses, share identities or copy
   an existing adopted state into a second active container.
4. An image pull does not install Mac aliases, PF policy or the bounded
   privileged helper. Those are a separate, exact host setup, not root
   privileges embedded in the image. The alpha does not automatically migrate
   the existing production installation.

## Release decisions and remaining gates

The owner's final approval and actual publication are now recorded above.
They are not a new copyright, firmware-rights or independent legal attestation.
Public container visibility remains a separate owner decision, followed by
anonymous pull verification; neither occurred in this release workflow. The
[issue #4 distribution review](legal/alpha-distribution-0.1.0a1.md) separates
retained technical evidence from missing review. The existing non-audit release
gate, exact source fingerprint, current-main seven-job CI, protected environments,
standard signatures and final provider readback all continue to apply to alphas.
Earlier failed attempts remain in the distribution record; the successful
recovery does not turn their failures or missing cleanup into passing evidence.
The existing tag, signed assets and reviewed source fingerprint are unchanged.
