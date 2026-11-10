# Offline source archive / image inventory review

Progress toward issues #4 and #16, not release clearance.

`tools/source_inventory_check.py` compares a separately hash-pinned
`selected-upstream-source-delivery/1` manifest and its original archive bytes
with the four default image inventories (AI Key/AI Port, AMD64/ARM64).
It performs no network request, archive extraction, package execution, image
startup, signature, upload or approval mutation.

## Inputs and invocation

Keep source archives and CI artifacts outside the checkout. Obtain the two
`container-install-*` artifacts using the existing
[image inventory procedure](image-inventory.md), verify their ZIP digests against
the independently trusted CI receipts, and retain their source revision.
A self-consistent JSON receipt is not independent evidence of its origin.

Use an independently retained SHA-256 for the source manifest; do not calculate
a replacement digest merely to admit a changed manifest. The expected revision
is a full 40-character commit ID, not a branch name or prefix.

```sh
python tools/source_inventory_check.py \
  --sources /external/review/sources \
  --manifest-sha256 EXPECTED_64_HEX_MANIFEST_SHA256 \
  --revision EXPECTED_40_HEX_IMAGE_SOURCE_COMMIT \
  --inventory /external/review/container-install-amd64 \
  --inventory /external/review/container-install-arm64 \
  > /external/review/source-image-report.json
```

The example paths are placeholders. Use an existing nonsynchronized review
directory, not iCloud Drive or a NAS destination synchronized into iCloud.

Exit codes:

- **0:** current-revision matrix with an archive candidate for every catalogued
  package. This is still **not** complete corresponding-source or legal approval.
- **1:** structured report produced, but images are stale or package candidates
  are missing.
- **2:** malformed, changed, missing or inconsistently bound input was refused.

## What is checked

- Manifest digest, schema, exact listed count and byte total; each listed source
  file's actual size and SHA-256. Duplicate paths, traversal and symlinks inside
  the selected source directory are refused. Unlisted files are not admitted
  as source candidates.
- Both architectures and both profiles, completed installation/cleanup fields,
  image configuration ID, revision, nonce and profile bindings.
- Exact SBOM and license-companion digests, using the existing companion reader
  to validate retained original notice bytes and subject bindings.
- The distinct CycloneDX operating-system entry against the receipt, separately
  from package and file entries; package count and unique references.
- Debian source name and explicit source version, when present. No heuristic
  stripping of epochs or binary rebuild suffixes.
- Python names normalized according to the usual hyphen/underscore/dot rule,
  with exact versions. Python, Debian, Rust and native-source namespaces are
  kept separate. The interpreter signature `python` has the explicit
  `interpreter/cpython` mapping. Other binary names are not guessed.
- Exact expected revision. An ancestor, equal dependency lock or green CI badge
  cannot make historical images current. No automatic tree-equivalence waiver.

Every package retains its SBOM reference, source candidate identity and matching
manifest paths. `archive_candidate` means only name/version agreement with
verified archived bytes. It does **not** prove those sources generated the
binary, that bundled dependencies are covered, or that redistribution is
approved. The project's own package is not silently satisfied by the upstream
archive collection.

## Actual historical replay, 10 November 2026

The retained PR308 inventory revision is
`e2a9ed7999dc45103a2542cc53013473bae4b524`.
The requested current main revision is
`973904631db4b45307dc59091730b9f9b3cf0bcc`.
These are deliberately reported as different.

Source manifest SHA-256:
`16950cce979c153d67f18f0d9f940d0fdff6e4d663890c110c492283add8e218`.

All 761 listed original files, totaling 1,288,233,863 bytes, passed byte
verification. Per-image package candidate results:

| Architecture | Profile | Candidates | Needs evidence |
| --- | --- | ---: | ---: |
| AMD64 | AI Key | 329 | 16 |
| AMD64 | AI Port | 329 | 16 |
| ARM64 | AI Key | 325 | 16 |
| ARM64 | AI Port | 325 | 16 |

Each image's 16 unmatched entries comprise 14 bundled launcher binary records
and two project-package records. This is an automated mapping gap, not a claim
that all their source bytes are unavailable. Existing detailed native-library
review must still be consulted; those relationships must not be guessed from
similar names.

The first real replay exposed the separate CycloneDX OS entry; it is now
validated against the OS receipt rather than counted as a package. The corrected
replay exits 1, as required for historical inputs and unresolved packages.

Current CI artifact API requests for run `42256417344` returned `Forbidden`
in this session. No current-image equality, new build, signing, publication,
deployment, native Mac acceptance or issue closure is claimed. The next actual
matrix must come from independently verified current CI artifacts. Optional
profiles, the database image, complete build/patch correspondence, recipient
delivery and independent origin/rights decisions remain open.
