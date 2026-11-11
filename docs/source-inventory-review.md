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

The initial CI artifact API requests for run `42256417344` returned `Forbidden`.
That failed attempt remains part of the historical record. The authenticated
retrieval below supersedes the access blocker, not the unresolved source or
rights decisions.

## Authenticated four-image replay, 11 November 2026

The already configured native GitHub credential path returned the expected
account and complete artifact metadata. Both ZIPs were downloaded and their
actual SHA-256 compared with the GitHub artifact digest before extraction:

| Artifact | GitHub artifact ID | ZIP SHA-256 |
| --- | --- | --- |
| container-install-amd64 | 13523820155 | `f1a57ead602b67128fd4b63d9118d0d62dda2c813a1c25c83e9da967007020aa` |
| container-install-arm64 | 13523570466 | `9d64dc5a48dcdeb9cebfa676aface3d13736dbbc6d88965ece6b7ed35c83a03e` |

[Successful CI run](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/42256417344).
Its PR head is `c97d96a3a288e89b6824d1957cd16992f25b9068`, but the inventories
correctly record the actual checked-out PR merge commit
`e2f619b8183346bc1cdb0917b8f6f09e5c0fac7f`. That commit was fetched and a
complete Git tree diff against main `973904631db4b45307dc59091730b9f9b3cf0bcc`
was empty. The checker was run against **the exact inventory merge revision**;
this separate tree-equivalence observation is not a revision-check waiver.
A first replay against the PR head correctly reported a revision mismatch.

All 761 source files (1,288,233,863 bytes) again matched the independently
retained manifest digest. For each profile, AMD64 has 329 archive candidates
and 16 unresolved records; ARM64 has 325 and 16. The unresolved set remains
14 bundled launcher records and two project-package records. Exit status is
1 because unresolved source candidates remain, even with exact image revisions.

These artifacts qualify the retained main tree above, **not future changes**
or a signed release. The checker and host changes on the new branch require
their own exact-head CI. No corresponding-source completeness, binary rebuild,
signing, release publication or issue closure is claimed. Optional profiles,
the database image, complete build/patch correspondence, recipient delivery
and independent origin/rights decisions remain open.

### Unresolved-record investigation

The 16 records are no longer unidentified dependencies. Exact SBOM location
properties in all four images identify:

- Six Windows launchers under `pip/_vendor/distlib`, supplied by pip 25.0.1.
  Its original source archive's `src/pip/_vendor/vendor.txt` pins distlib 0.3.9.
  The separately retrieved original `distlib-0.3.9.tar.gz` is 613,923 bytes,
  SHA-256 `a60f20dea646b8a33f3e7772f74dc0b2d0772d2837ee1342a00645c81edf9403`.
  Its `PC/launcher.c`, Visual C++ project files and solution are present.
  [Exact upstream version](https://pypi.org/project/distlib/0.3.9/).
- Eight Windows launchers under `setuptools`. The already verified setuptools
  84.0.0 source archive includes `launcher.c`, `tools/build_launchers.py`,
  the launcher manifest and the binary files.
- Two `local-aikey` records: build-tree `egg-info` and installed `dist-info`,
  not two additional third-party packages. Their source subject is the exact
  CI checkout revision above, rather than a similarly named PyPI archive.

This is path/version/source-location evidence, not a byte-for-byte launcher
rebuild or origin/rights clearance. The automated checker intentionally keeps
these records unresolved; no name-only alias or blanket exemption was added.
The extra distlib archive is retained separately with its upstream digest and
receipt; it does not silently change the existing 761-file manifest.


## Automatic bundled-source resolution

The checker now resolves the 14 observed launcher records through their exact
SBOM locations and a unique installed Python owner, not through binary-name
aliases. Only the observed Python 3.12 site-packages layout is admitted:

- Six exact pip/distlib executable paths, `Simple Launcher` version 1.1.0.14.
  The image must contain exactly one pip distribution with its matching
  versioned metadata location. Its verified source archive must contain one
  unambiguous `distlib==VERSION` vendor pin. That exact distlib source archive
  must contain regular, nonempty C source and both CLI/GUI project files.
- Eight exact setuptools executable paths, with their observed `UNKNOWN`
  scanner version. A unique installed setuptools owner and its matching
  versioned metadata location are required. That exact source archive must
  contain regular C source and the launcher build script.

All archives must already belong to the hash-pinned source manifest. Source
bytes are rechecked when reading members. Archive size, declared uncompressed
extent, member count and selected member size are bounded; duplicate selected
members and links are refused. No archive is extracted to the filesystem and
no package, compiler or build script is executed. Missing or conflicting owner,
path, vendor version or source members never become a guessed candidate.

Resolved rows retain the binary identity and location, owner/version, selected
source archive/member paths and supporting vendor archive. They remain
`archive_candidate`, **not** proof that the C source built the included PE file.
License, patches, build correspondence and release gates are unchanged.

An actual replay against the authenticated PR311 four-image inventories and
the separately pinned 764-file source collection yields:

| Architecture | Profile | Archive candidates | Still needs evidence |
| --- | --- | ---: | ---: |
| AMD64 | AI Key | 343 | 2 |
| AMD64 | AI Port | 343 | 2 |
| ARM64 | AI Key | 339 | 2 |
| ARM64 | AI Port | 339 | 2 |

The remaining two records per image are project build-tree and installed
metadata. They are not assigned a third-party source archive. The report still
exits 1, and `complete_corresponding_source` and `release_approved` remain false.
No input receipt or old failed result is rewritten. These retained image
inventories qualify their embedded revision, not a future image build.


### Separate project-source subject

Optionally add `--project-archive EXACT_COMMIT_SOURCE.tar` and
`--project-archive-sha256 TRUSTED_64_HEX_DIGEST` to the invocation. Supply both
or neither. Generate the tar from an authenticated, verified exact Git commit
with `git archive --format=tar COMMIT`, not from a working directory; retain its
digest separately. A self-generated replacement hash is not independent origin
proof. The reader performs no Git, network or build operation.

The bounded archive byte snapshot must match the supplied digest. Its Git PAX
commit field must equal the expected full inventory revision, and it must have
unique safe regular/directory members, project metadata, license and package
source. Name/version and the exact observed build-tree/installed metadata paths
are checked separately for each image. An ordinary upstream manifest row named
`local-aikey` cannot satisfy this requirement. Stale image revisions never
inherit the current project's archive. The report records the separate archive
digest, commit and module count without claiming a build or rights attestation.

The retained authenticated inventory revision
`a4975f8d3e039d8398265b85b660c24865750a22` was archived directly from its fetched
Git object. Its 9,840,640-byte tar has SHA-256
`18cd580e1c49359d7d9b6fa2f0fcdd879ae2e37a60260c05d30ab9ea6516634f` and
181 package source modules. With that exact separately pinned input, the real
matrix has **345 candidates per AMD64 profile and 341 per ARM64 profile**, no
unmatched catalogued package records, and exits 0. Without it, the two project
records per image remain unresolved and exit status remains 1.

This completes candidate-source mapping for these retained four default images
only. `complete_corresponding_source=false` and `release_approved=false` are
unchanged. Vendored dependencies beyond the catalogued records, binary rebuilds,
patch/build obligations, optional images/models, recipient delivery and genuine
human provenance/rights/release decisions remain separate.


## Exact merged-main refresh, 11 November 2026

The successful main-branch [native image run](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43024747881)
checks out exactly `c92686a2916afaa656f6500d63a000563d1ea9a2` for all four
default profile/architecture combinations; no PR merge/head equivalence waiver
is used in this refresh. Both downloaded ZIPs match their authenticated GitHub
artifact metadata before bounded extraction:

| Artifact | ID | ZIP SHA-256 |
| --- | --- | --- |
| container-install-amd64 | 13857136211 | `69bda1371cbdcfb99706f5136b557e5de150eb092dc7aff2f5b68637072f6f09` |
| container-install-arm64 | 13855903610 | `a42ae8346636d4cbaf9d78c394cbaebe3a83fc1e24f4a69a8e9f8aabd8b7dfef` |

The unchanged 764-file upstream source manifest is pinned to
`e97fc8ea5f02166fe9d7280c7b16dc5f3ceed911077ddb191c7e5cea7d38bdb8`.
All 1,288,871,052 original bytes match. The exact authenticated main Git object
was archived separately: project tar SHA-256
`7fbd923defc34b291d420204241cfa2538f209a88591eefa8c4cc071bc45d62d`,
183 package modules. The actual source checker exits zero: 345 archive
candidates per AMD64 profile, 341 per ARM64 profile, no unmatched catalogued
package records, both architectures and profiles at the exact expected revision.
The retained complete report SHA-256 is
`1facbfec02f99dfa215692b933a2f07eee5d56e78079adba0e2b6356ef1afb5f`.

This refresh is not a binary rebuild, complete corresponding-source audit,
optional-profile/database inventory, rights approval, signature, tagged release
or automatic approval of later source/images. Both completeness and release
approval fields remain false; #4/#16 retain their separate original gates.


## Exact post-PR315 four-image subject

A separate review qualifies the exact main subject
`e1970e4c214fb45a16e2307d4eeda26fc5ddde07`, not a future documentation commit.
[Container CI run 43031655628](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43031655628)
and [security/quality run 43031655506](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43031655506)
completed successfully on that subject.

| Artifact | GitHub artifact ID | Independently compared ZIP SHA-256 |
| --- | --- | --- |
| container-install-amd64 | 13860279997 | `00e84dbc0228c8245d8f028913f9cd593187b402450dcca85495940d1c444546` |
| container-install-arm64 | 13861515597 | `16c92d58229f23598f93a29feb26cd0e190a442027a85d14a5da7c771052346a` |

The checker exits **0**: 764 source files / 1,288,871,052 bytes match the
retained source manifest `e97fc8ea5f02166fe9d7280c7b16dc5f3ceed911077ddb191c7e5cea7d38bdb8`.
Both AI Key and AI Port profiles have 345 candidates on AMD64 and 341 on ARM64,
with no unmatched catalogued packages. The exact project Git archive contains
183 source modules and has SHA-256
`5ec1a9052fb4ea53005d5e5d0982480fd40db71c8759a5976dbe3aea1ad033da`.
The copied private runner retained an older subject in its archive filename;
its checked content, explicit pin and report identify **e1970e4**, not that
inherited basename. No filename-based revision waiver was used.

Report SHA-256:
`24a0ed04e025b9b2aec3d9a476f37d9cc8c672cd95bc5a8e8b79f1bb2cad5e6f`.
This remains **source-candidate mapping**, not complete corresponding source,
reproducible binary builds, optional/database-profile coverage, legal origin/
redistribution attestation, a signature or release approval. Issues #4/#16
retain those original requirements. No production image or model was changed.
