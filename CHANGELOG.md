# Changelog

A source/package version is not a completed or supported public-release claim.
Use the repository's Releases and its signed manifest for actual availability.

## 0.1.0a1 alpha specification

- Prepare default AI Key/AI Port OCI images for native Linux AMD64/ARM64;
  Apple Container uses the same ARM64 image, without bundled model weights.
- Accept explicit alpha versions in the owner-gated publisher and its
  attempt-bound image-reference checks; all existing review gates remain.
- Record [delivery scope and remaining prerequisites](docs/alpha-release.md).
  This entry alone does not claim publication or close the original issues.

## Unreleased

- Reworked public installation/deployment documentation and removed installation-
  specific camera labels, addresses, user paths and private migration notebooks.
- Removed obsolete tests of a private ten-module September image patch plan.
  Current full-package/image installation checks remain the shipping contract.
- Generalized readiness output and newly generated LaunchAgent labels. Existing
  loaded agents are not renamed automatically; inspect/unload the predecessor
  before installing one replacement, as described in the Apple guide.

- Added complete local controller-trust, configuration, camera-reference and
  rollback workflows for Key and Port profiles. ONVIF references do not provide
  ONVIF media ingest, PTZ or recording.
- Added guarded index export/rebuild/rollback tooling and explicit benchmark
  attempt accounting. Actual benchmark target failures remain visible; completing
  the benchmark does not certify model quality.
- Added native Linux AMD64/ARM64 installed-source/state checks and whole-image
  CycloneDX inventories with checksum-pinned Syft. Unknown licenses/PURLs remain
  unknown and do not grant redistribution rights.
- Added fenced host-upgrade intent, observed transitions, command-lifetime
  supervision and explicit bounded recovery. Isolated process/source compatibility
  is separate from native Mac/NAS power-loss, restore and sustained-operation proof.
- Added the owner-gated manual publisher, standard GitHub OIDC/Sigstore bundles,
  exact candidate verification and create-only publication/reconciliation. Human
  evidence, destinations, environments and first publication remain pending.

For versioning, actual platform boundaries, verification and interrupted attempts,
see the [release procedure](docs/releasing.md). The open issue tracker remains
the acceptance record; this changelog does not close its native/product criteria.
