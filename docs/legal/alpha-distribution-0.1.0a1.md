# Default-image alpha distribution review

Scope: [the requested 0.1.0a1 alpha](../alpha-release.md), not a declaration
that all original issue #4 criteria or legal prerequisites are satisfied.

## Existing concrete evidence

| Subject | Retained result | Limit |
| --- | --- | --- |
| Project license | Owner selected Apache-2.0; root license and package metadata agree | Does not establish rights of every contributor or firmware artifact |
| Project identity | Independent experimental local AI processor; no Ubiquiti affiliation | Compatibility naming is not manufacturer endorsement |
| Source/package contents | Existing full public-tree/package audits exclude firmware, models, private state/keys/traces/media | Automated content scanning is not protected-expression/ownership review |
| Default image notices | Original installed notices, CPython, native-library and Cryptography Rust material retained and delivered | Scanner SPDX completeness is not license clearance |
| Exact image/source candidates | Four e1970e4 default images mapped to 764 verified source files, 296 component/version pairs, 1,288,871,052 bytes | A named historical subject, not new alpha image bytes or proof of reproducible binary builds |
| Acquisition | Every one of those 764 retained original files has an exact HTTPS source URL, size and SHA-256 | Does not by itself supply recipients with complete corresponding source or establish redistribution approval |
| Native adoption | Actual isolated camera-free token-confirmed Mac adoption/restore recorded | Exact older guest/host subjects are named; not a blanket alpha/platform approval |

See the [source/image review](../source-inventory-review.md),
[third-party inventory](third-party-distribution.md),
[native-library notices](native-library-notices-20261106.json) and
[Cryptography Rust notice evidence](cryptography-rust-components-20261106.json).
The pending statuses in [release-evidence.json](release-evidence.json) remain
pending; automated tools do not generate an owner's or lawyer's sign-off.

## Work that still has to be resolved for publication

- Bind the actual final alpha commit and four built image subjects to the
  original source/notice inventory; acquire any changed exact versions rather
  than accepting a stale previous-image record.
- Provide artifact-specific recipient source/notice delivery for the chosen
  binaries, including applicable copyleft components. A generic upstream page,
  metadata match or original-archive collection is not a completed delivery.
- Complete current code/history origin and contributor-rights review, with
  retained references to actual evidence instead of commit-author labels.
- Supply artifact-specific firmware/controller access, interoperability scope
  and the required legal review. Existing owner statements about public
  downloads and development outside employment do not answer every item.
- Record the exact reviewed source fingerprint and publication destinations,
  configure the required protected owner-review environments, and qualify the
  complete signed candidate before publication.

The relevant [release-readiness gate](release-readiness.md) explicitly says:

> An agent must not certify facts it cannot know or sign an owner's attestation.

This alpha request authorizes engineering preparation and publication once the
real prerequisites are met. It does not turn unknown origin/rights facts into
verified facts, change the gate to audit-only, or provide a new legal opinion.
No publication, signature, public tag, image digest or issue closure is claimed
by this review specification.
