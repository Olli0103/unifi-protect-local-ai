# Artifact-specific community release readiness

A green automated audit is not a rights decision or permission to publish.
The owner supplies evidence and approvals for the exact source snapshot.
The [evidence record](release-evidence.json) uses `community-release-evidence/2`.

## Required checks

| Check | Package (wheel/sdist) | Image | Concrete completion criterion |
| --- | --- | --- | --- |
| `license_selection` | Required | Required | Owner confirms Apache-2.0 for the project, with the included license and notices. |
| `development_statement` | Required | Required | Owner records development outside assigned employment duties, without employer code; unresolved employer rights remain visible. |
| `contributor_rights` | Required | Required | Review human authors, historical contributions and AI co-author metadata, including rights to the selected license; labels alone are not proof. |
| `code_origin` | Required | Required | WP1 and WP2 accepted, including historical research/history review and zero unaccounted retained interface facts. Scoped source mapping is not itself a rights attestation. |
| `interoperability_scope` | Required | Required | WP1 accepted: necessity, analyzed minimum, missing public information and permitted disclosure recorded. |
| `owner_risk_decision` | Required | Required | Owner records the E1–E11 decision and answers/resolves the concrete outstanding rights/access questions. No blanket lawyer approval is manufactured. |
| `image_licenses` | Not required | Required | WP3 accepted: exact image digests, licenses/notices, corresponding-source and delivery chain, with current-revision `source_inventory_check` exit 0. Candidate matching alone is not complete-source approval. |

Every effective check is still `needs_evidence`. A `verified` entry needs a
nonblank reviewer and retained-evidence reference. A matching
`reviewed_snapshot_sha256`, active nonempty LICENSE and clean source inputs
remain mandatory. Any tracked input change invalidates the fingerprint.
An agent must not fill the owner's declarations.

## Schema migration and nonblocking records

The tested `migrate_evidence` function preserves the old schema-1 record under
`legacy_evidence` for traceability but resets all effective checks, publication
approval and snapshot. Historical approvals are not new approvals.

- History review is included in `code_origin`.
- Dependency redistribution obligations are included in `image_licenses`.
  The source-only package declares dependencies in
  [pyproject metadata](../../pyproject.toml) and the
  [runtime lock](../../requirements-runtime.lock); it does not bundle them.
- `firmware_authorization` becomes nonblocking `research_record`. This does not
  authorize new firmware access or erase historical rights questions.
- `legal_review` becomes the concrete `owner_risk_decision`.
- AI Port fresh adoption is a functionality/known-limitation record, not a
  distribution-rights gate. See [compatibility limits](../compatibility.md).
- Model license approval is not a package gate because no weights ship in these
  artifacts. Existing prohibited-suffix and binary-content checks still reject
  bundled weights, firmware, private keys, private state and camera media.

Private purchase/access/employment records stay outside the repository.
The [provenance record](provenance.md), [licensing](licensing.md) and
[third-party distribution](third-party-distribution.md) remain review inputs.

## Commands and publication scope

```sh
python tools/community_release_check.py --audit-only --profile package
python tools/community_release_check.py --profile package --dist dist
python tools/community_release_check.py --profile image
```

Audit-only always reports `release_approved: false`. The default CLI profile
is conservatively `image`; specify the artifact explicitly.
Package mode requires only the six checks above plus the source snapshot
and structural/content checks; pending image evidence does not block it.

The [owner-gated workflow](../releasing.md) has a required `profile` input.
`package` builds, signs and verifies wheel/sdist plus package metadata, with
no image jobs, registry login, image attestations or Docker reads/writes.
`image` additionally requires image clearance and both native architectures.
Both modes retain all seven prerequisite CI jobs, exact public-tag/source
bindings, fresh non-audit gates, protected staging/final environments,
standard signature verification and provider asset-digest readback.
The package consumer explicitly uses `package`; image publication uses fresh
`image` preparation. Neither mode is dispatched by this change.

First distribute wheel/sdist after owner acceptance; image publication follows
WP3 and the separate owner image decision. No tag, upload or signature is
created by implementing or testing these paths.
