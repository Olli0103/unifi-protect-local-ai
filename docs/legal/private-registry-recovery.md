# Private registry recovery for the original alpha candidate

The original source/tag and source-delivery evidence are unchanged. Execution
policy now stages both image profiles in the existing, positively private
`ghcr.io/olli0103/local-aikey-0.1.0a1` package. Each profile has its own
`<profile>-0.1.0a1-<amd64|arm64|index>-run<current-run-id>` tag and immutable
manifest digest. The signed candidate retains separate profile, native
architecture, SBOM and provenance bindings. No new registry package is created.

This layout is available only for the exact original source, original draft
444049704 and original run 43402688428, with the finite reviewed incident run
43865727276 appended to the previous reconciliation chain. Unknown intervening
runs, changed job graphs, reruns and changed original artifacts still refuse.
Both protection environments and both seven-job source/policy qualifications
remain mandatory. The final public-release environment is not approved by this
repair, and no package visibility change occurs in the pipeline.

## Observed completed recovery (2026-11-16)

[Run 43920818331](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43920818331)
built fresh native images, completed cleanup/signature/consumer checks and,
after separate final owner approval, published the original source/package
release. [The alpha record](../alpha-release.md) identifies the exact signed
subjects. **The shared registry package remains private.** The successful
publication is not an anonymous-pull result or permission to change visibility.
The finite reviewed history and earlier failures remain retained; this is not a
standing authorization for another attempt.

## Incident retained, not erased

Run 43865727276 created a real AI-Key registry version. The package was observed
public without authorization and contained privately at 2026-11-16T12:34:21Z.
Downloads during the public phase cannot be excluded. Its exact version ID,
tag and digest are pinned in `recovery-private-registry.json`; it must remain
unchanged. Both native job cleanups failed. Those failures are verified as
failures against the actual provider step graph, never reclassified as success.
The temporary old runners and their local resources cannot now be inspected;
no historical zero-residue assertion is made. Old native images, signatures,
runner state and package artifacts are not reused. Fresh runners rebuild the
unchanged source and must prove their own complete cleanup before handoff.

The full active registry version catalogue is checked with owner-authenticated
read-only package access before effects. It must contain the exact retained
incident version; all other versions must have only current-run profile-specific
tags. Unknown or untagged versions refuse. Existing package privacy and source
repository association are positively rechecked before every registry write.
Registry blobs not represented by a package version are not claimed absent;
they are never an adopted input. A failed push observation removes only the
new local alias in a `finally` path; it never deletes a registry version.

This is not a public bootstrap, private-after-push fallback, blanket history
admission or permission to reuse run 43865727276. It enables one deliberate new
attempt only after the exact repair and current registry state qualify.
