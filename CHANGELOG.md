# Changelog

A source/package version is not a completed or supported public-release claim.
Use the repository's Releases and its signed manifest for actual availability.

## Unreleased

- Update README, deployment/release guides and maintenance records to distinguish
  the published alpha source/packages from private container images. These are
  post-release documentation changes, not changes to the existing alpha tag.

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
  evidence, protected environments and owner decisions remain exact-snapshot
  gates. The first completed publication is recorded below, not inferred from
  implementation of the publisher.

## [0.1.0a1](https://github.com/Olli0103/unifi-protect-local-ai/releases/tag/v0.1.0a1) — 2026-11-16

- Published the first signed experimental GitHub prerelease from source
  `a3da9c21715dade37fbe3a25529fa85fd17dc430`, after the owner's final approval.
  [Release run 43920818331](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43920818331)
  completed successfully with 25 uploaded, digest-verified assets: wheel, sdist,
  corresponding source, notices, inventories, checksums and Sigstore bundles.
- Built and signed default AI Key and AI Port images on native Linux AMD64/ARM64;
  installed-source/state checks, cleanup and the final candidate consumer passed.
  Both profiles use distinct immutable subjects in one existing versioned GHCR
  package. **Images remain private**, not available for anonymous pulls.
- Recovered the original draft without moving the source tag, replacing assets
  or adopting failed-run images. Earlier failures and the registry incident are
  retained in the [distribution record](docs/legal/alpha-distribution-0.1.0a1.md).
- Record [exact delivery subjects and remaining limits](docs/alpha-release.md).
  This alpha does not establish native feature parity, independent-installation
  acceptance, model quality, sustained operation or a supported release line.

For versioning, actual platform boundaries, verification and interrupted attempts,
see the [release procedure](docs/releasing.md). The open issue tracker remains
the acceptance record; this changelog does not close its native/product criteria.
