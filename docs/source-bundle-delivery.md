# Same-release source delivery for the default images

This implements WP3's transport and fail-closed source checks. It does not
declare the selected upstream sources complete corresponding source, rebuild
all third-party binaries or fill the owner's rights approvals.

The public destinations are `ghcr.io/olli0103/local-aikey` and
`ghcr.io/olli0103/local-aiport`. Device protocol identities remain unchanged.

## Owner inputs

After reviewing the actual sources and build/patch obligations, the owner
provides a retained GitHub Actions artifact in this same repository containing
the original upstream source collection: `manifest.json` at its root and every
listed original archive at its exact manifest path. The established collection
has 764 files; no firmware, analysis extracts, model weights or private state
belongs in this artifact. Keep the archive collection out of the repository.

Record the artifact's run ID, exact artifact name and independently retained
manifest SHA-256 in `source_delivery` in
[release-evidence.json](legal/release-evidence.json). These three values are
deliberately unset until the owner supplies the real artifact. The workflow
does not guess a digest, choose a public mirror or download new dependencies.

The `image_licenses` approval and reviewed source snapshot remain owner-only.
A checker exit zero supplies package/source-candidate mapping, not the missing
human completeness or redistribution decision. Optional detector/model and
database images are outside this four-default-image matrix.

## Ordered workflow

1. The owner dispatches the exact tagged main commit with `profile: image`.
   The original read-only checks require the image evidence profile, exact
   source/tag, all seven CI jobs and existing protected environments.
2. Protected staging approval permits the existing create-only empty draft
   reservation. It does not yet publish an image or upload release assets.
3. The new source job downloads the owner-pinned original source artifact and
   both exact-revision native qualification artifacts. Maintained artifact
   download actions verify transport digests. The existing source checker
   validates every source manifest byte/size/hash and all four inventories.
4. `release_sources.py` invokes the actual
   [source-inventory checker](../tools/source_inventory_check.py) and requires
   **exit 0** at the exact release commit. It generates the project source with
   `git archive HEAD`, including the license, build/install recipes and this
   workflow. Unmatched packages or a stale revision stop the pipeline.
5. A deterministic uncompressed TAR contains the upstream originals, project
   Git archive and exact inventory inputs. Files are split below GitHub's 2 GiB
   asset limit (2 GiB minus 1 MiB). Each ordered part has its own SHA-256 and byte
   count; a separate hash binds the concatenated TAR. The generated canonical
   `source-bundle.json` is also hashed.
6. Every image/asset consumer receives only this run's validated source
   delivery. Before registry/asset upload, it reconstructs bounded regular
   members in a private temporary directory and reruns the source checker.
   The project's archive must match a fresh local `git archive HEAD`
   byte-for-byte. Traversal, symlinks, hardlinks, duplicate members, unlisted
   files, wrong parts, wrong hashes and incomplete inventories are refused.
7. Native rebuilds still have to match the qualified package catalog and
   original license/notice bytes before image push; existing installed-source
   and state probes, cleanup and exact immutable-image checks remain required.
8. The source index and all parts are included in the **same GitHub release**
   asset set as wheel/sdist. Every immutable image entry in signed
   `release.json` includes `source_bundle`: index URL + SHA-256,
   `archive_sha256`, and ordered parts with URLs, sizes and individual hashes.
   The standard root attestation signs release.json and SHA256SUMS, binding the
   actual source part bytes transitively; no nonexistent direct-part signatures
   are claimed. Upload and provider digest read-back cover the source assets.
9. The existing protected final approval and standard signature/consumer
   checks still precede public release. No tag, registry push, signing or
   release dispatch is performed by implementing or testing this path.

## Recipient verification

Retrieve and verify the signed release.json and SHA256SUMS as described in
[releasing](releasing.md). Find the exact image digest's source_bundle record,
download its index URL and verify that file against its `sha256`. Download
each listed part from the same release and verify its individual hash/size.
Concatenate parts in the recorded order and verify `archive_sha256` before
reading the TAR. URLs alone are neither delivery proof nor a source offer.

Both Dockerfiles render
[the image notice template](legal/image-sources-template.md) to
`/usr/share/local-aikey/SOURCES.md`. Its URL is supplied only through
`SOURCE_BUNDLE_URL`; no real-looking default is embedded in a Dockerfile.
A direct development build without the argument explicitly says UNPUBLISHED.
The native qualification/publishing build derives the exact versioned
release.json URL from project metadata. The existing image inventory collector
captures the notice's original bytes and fails if it is missing or unrendered.
All four default image/architecture combinations use that same requirement.

## Scope of evidence

Tests use fictional source archives, real temporary Git archives and synthetic
four-image inventories. They run the actual checker and actual bundle
producer/consumer, including forced multipart boundaries and negative cases.
They are not native image builds or legal approvals. Native CI must separately
prove the notice in all four built images; a source build alone cannot do so.
