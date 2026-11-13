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

## Recorded decision and snapshot boundary (2026-11-13)

At the schema-2 migration, all effective checks were reset to `needs_evidence`.
That is historical, not the status of the subsequently reviewed alpha source.
For `a3da9c21715dade37fbe3a25529fa85fd17dc430` (tag `v0.1.0a1`), the
[evidence record](release-evidence.json) contains all seven checks as `verified`
by `Olli0103`, with references to the retained owner decisions and explicit
test-only source-transition confirmation. Both non-audit profiles passed for
reviewed input fingerprint
`ad5ac45a4c12e863241e93f3f1a9fdd422b58a8ddd25f1e3e7b4d152db4499cd`.
This records the owner's bounded rights/risk/source decision for preparation,
not an agent's legal finding or a guarantee of rights. The nonblocking
`research_record` remains `needs_evidence`; historical firmware-access rights
are not established and no further firmware analysis is authorized.

The `publication` entry is also `verified`, but its retained decision authorizes
**private staging only**, not final candidate publication or public image
visibility. The attempted staging failed after creating a private draft; no
signed candidate or completed public release resulted. See the dated
[alpha distribution status](alpha-distribution-0.1.0a1.md).

A `verified` entry needs a nonblank reviewer and retained-evidence reference.
A matching `reviewed_snapshot_sha256`, active nonempty LICENSE and clean source
inputs remain mandatory. Any tracked input change, including these documentation
corrections, invalidates that fingerprint (only the evidence record is excluded).
The retained approval belongs to the named alpha snapshot, not a later tree:
these corrections do not rebind it, move the tag or authorize another staging
attempt. Any successor release source requires exact-snapshot review and fresh
qualification. An agent must not fill the owner's declarations.

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
`image` preparation. This documentation correction dispatches neither mode.

Distribution still requires the final owner decision on the actual signed
candidate. The recorded source/image preparation decisions do not substitute
for that gate. Documenting or testing these paths creates no tag, upload or
signature; the dated alpha status separately records the actual tag and failed
private-staging attempt.
